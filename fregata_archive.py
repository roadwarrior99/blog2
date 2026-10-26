"""
fregata_archive.py — read-only view of the Fregata NVR's S3 archive.

The Fregata host uploads every finished review item hourly to a private,
Object-Locked bucket laid out as::

    <camera>/<YYYY>/<MM>/<DD>/<review id>/clip.mp4
                                         /snapshot-<event id>.jpg
                                         /review.json

This module powers the logged-in ``/fregata`` page:

  * storage usage, ingest rate and estimated cost, from a (cached) listing.
  * the last two days of captures, labelled from each ``review.json``.
  * a streaming proxy so the browser never talks to S3 directly — the bucket
    stays private and no presigned URLs leave the server. Range requests are
    honoured (and capped) so ``<video>`` can seek without tying up a waitress
    thread for the length of a 100 MB clip.
"""

import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

BUCKET = os.environ.get("FREGATA_ARCHIVE_BUCKET", "fregata-archive-631538352062")
REGION = os.environ.get("FREGATA_ARCHIVE_REGION", "us-east-1")
RETENTION_DAYS = int(os.environ.get("FREGATA_RETENTION_DAYS", "90"))

RECENT_HOURS = 48
RATE_WINDOW_DAYS = 7         # ingest rate is averaged over (up to) this many days
LISTING_TTL = 600            # seconds a bucket listing is reused
STREAM_CHUNK = 4 * 1024 * 1024   # max bytes served per range request
READ_SIZE = 64 * 1024

# S3 Standard list prices, us-east-1 (USD).
PRICE_GB_MONTH = 0.023
PRICE_PUT_PER_1000 = 0.005

KEY_RE = re.compile(
    r"^(?P<camera>[A-Za-z0-9_-]+)/(?P<date>\d{4}/\d{2}/\d{2})/"
    r"(?P<review>(?P<start>\d+\.\d+)-[A-Za-z0-9]+)/(?P<name>[A-Za-z0-9._-]+)$"
)
MEDIA_NAME_RE = re.compile(r"^(clip\.mp4|snapshot-[A-Za-z0-9.-]+\.jpg)$")
RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")

_client = None
_listing = {"at": 0.0, "objects": None}
_listing_lock = threading.Lock()
_review_meta = {}            # review.json key -> parsed dict (objects are immutable)


class MediaNotFound(Exception):
    pass


class RangeNotSatisfiable(Exception):
    def __init__(self, size):
        self.size = size


def _s3():
    # Lazy so app.py's boto3.setup_default_session() (dev profile) applies.
    global _client
    if _client is None:
        _client = boto3.client("s3", region_name=REGION)
    return _client


# ─────────────────────────────────────────────────────────────────────────────
# Listing
# ─────────────────────────────────────────────────────────────────────────────
def _list_objects():
    with _listing_lock:
        if _listing["objects"] is not None and time.time() - _listing["at"] < LISTING_TTL:
            return _listing["objects"]
        objects = []
        for page in _s3().get_paginator("list_objects_v2").paginate(Bucket=BUCKET):
            for obj in page.get("Contents", []):
                objects.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "modified": obj["LastModified"],
                })
        _listing.update(at=time.time(), objects=objects)
        logger.info(f"Fregata archive listing refreshed: {len(objects)} objects")
        return objects


# ─────────────────────────────────────────────────────────────────────────────
# Usage + cost
# ─────────────────────────────────────────────────────────────────────────────
def _captured_at(obj):
    m = KEY_RE.match(obj["key"])
    if m:
        return datetime.fromtimestamp(float(m.group("start")), timezone.utc)
    return obj["modified"]


def usage_summary(now=None):
    now = now or datetime.now(timezone.utc)
    objects = _list_objects()
    total_bytes = sum(o["size"] for o in objects)
    gb = total_bytes / 1024 ** 3

    summary = {
        "bucket": BUCKET,
        "retention_days": RETENTION_DAYS,
        "total_objects": len(objects),
        "total_bytes": total_bytes,
        "monthly_storage_cost": gb * PRICE_GB_MONTH,
        "bytes_per_day": 0,
        "objects_per_day": 0,
        "rate_window_days": 0,
        "projected_bytes": 0,
        "projected_monthly_cost": 0,
        "listed_at": datetime.fromtimestamp(_listing["at"], timezone.utc),
    }
    if not objects:
        return summary

    # Average over the last RATE_WINDOW_DAYS, or since the first capture when the
    # archive is younger than that (never less than an hour, to avoid silly rates).
    # Capture time, not upload time: the first sync backfills older items.
    first_capture = min(_captured_at(o) for o in objects)
    window_start = max(first_capture, now - timedelta(days=RATE_WINDOW_DAYS))
    window_days = max((now - window_start).total_seconds() / 86400, 1 / 24)
    in_window = [o for o in objects if _captured_at(o) >= window_start]
    bytes_per_day = sum(o["size"] for o in in_window) / window_days
    objects_per_day = len(in_window) / window_days

    # Lifecycle expires objects at RETENTION_DAYS, so at a steady rate the bucket
    # levels off at rate × retention.
    projected_bytes = bytes_per_day * RETENTION_DAYS
    put_cost = objects_per_day * 30 / 1000 * PRICE_PUT_PER_1000
    summary.update(
        bytes_per_day=bytes_per_day,
        objects_per_day=objects_per_day,
        rate_window_days=window_days,
        projected_bytes=projected_bytes,
        monthly_put_cost=put_cost,
        projected_monthly_cost=projected_bytes / 1024 ** 3 * PRICE_GB_MONTH + put_cost,
    )
    return summary


def per_camera_bytes():
    totals = {}
    for o in _list_objects():
        m = KEY_RE.match(o["key"])
        camera = m.group("camera") if m else "(other)"
        totals[camera] = totals.get(camera, 0) + o["size"]
    return dict(sorted(totals.items(), key=lambda kv: -kv[1]))


# ─────────────────────────────────────────────────────────────────────────────
# Recent captures
# ─────────────────────────────────────────────────────────────────────────────
def _load_review(key):
    if key not in _review_meta:
        try:
            body = _s3().get_object(Bucket=BUCKET, Key=key)["Body"].read()
            _review_meta[key] = json.loads(body)
        except (ClientError, ValueError):
            logger.warning(f"Fregata review metadata unreadable: {key}")
            return {}
    return _review_meta[key]


def recent_captures(hours=RECENT_HOURS, now=None):
    """Review items that started in the last ``hours``, newest first."""
    cutoff = (now or datetime.now(timezone.utc)).timestamp() - hours * 3600
    reviews = {}
    for o in _list_objects():
        m = KEY_RE.match(o["key"])
        if not m or float(m.group("start")) < cutoff:
            continue
        r = reviews.setdefault(m.group("review"), {
            "id": m.group("review"),
            "camera": m.group("camera"),
            "start": float(m.group("start")),
            "clip": None,
            "clip_size": 0,
            "snapshots": [],
            "meta_key": None,
        })
        name = m.group("name")
        if name == "clip.mp4":
            r["clip"], r["clip_size"] = o["key"], o["size"]
        elif name.startswith("snapshot-") and name.endswith(".jpg"):
            r["snapshots"].append(o["key"])
        elif name == "review.json":
            r["meta_key"] = o["key"]

    meta_keys = [r["meta_key"] for r in reviews.values() if r["meta_key"]]
    with ThreadPoolExecutor(max_workers=8) as pool:
        metas = dict(zip(meta_keys, pool.map(_load_review, meta_keys)))

    out = []
    for r in reviews.values():
        review = metas.get(r["meta_key"], {}).get("review", {})
        data = review.get("data") or {}
        end = review.get("end_time")
        r.update(
            severity=review.get("severity", ""),
            objects=data.get("objects") or [],
            zones=data.get("zones") or [],
            duration=(end - r["start"]) if end else None,
        )
        r["snapshots"].sort()
        out.append(r)
    out.sort(key=lambda r: -r["start"])
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Streaming proxy
# ─────────────────────────────────────────────────────────────────────────────
def is_media_key(key):
    m = KEY_RE.match(key)
    return bool(m and MEDIA_NAME_RE.match(m.group("name")))


def _object_size(key):
    try:
        return _s3().head_object(Bucket=BUCKET, Key=key)["ContentLength"]
    except ClientError as e:
        raise MediaNotFound(key) from e


def open_media(key, range_header=None):
    """Fetch (part of) an archived clip or snapshot.

    Returns ``(status, headers, body_iterator)``. Open-ended or oversized
    ranges are trimmed to STREAM_CHUNK; browsers simply ask for the next piece.
    """
    content_type = "video/mp4" if key.endswith(".mp4") else "image/jpeg"
    kwargs = {"Bucket": BUCKET, "Key": key}
    m = RANGE_RE.match(range_header.strip()) if range_header else None

    if m and (m.group(1) or m.group(2)):
        if m.group(1):
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else start + STREAM_CHUNK - 1
            end = min(end, start + STREAM_CHUNK - 1)
            if end < start:
                raise RangeNotSatisfiable(_object_size(key))
            kwargs["Range"] = f"bytes={start}-{end}"
        else:  # suffix range: the last N bytes
            kwargs["Range"] = f"bytes=-{min(int(m.group(2)), STREAM_CHUNK)}"

    try:
        resp = _s3().get_object(**kwargs)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "InvalidRange":
            raise RangeNotSatisfiable(_object_size(key)) from e
        if code in ("NoSuchKey", "404", "AccessDenied"):
            raise MediaNotFound(key) from e
        raise

    headers = {
        "Content-Type": content_type,
        "Content-Length": str(resp["ContentLength"]),
        "Accept-Ranges": "bytes",
        # Archived objects are immutable; keep them out of shared caches.
        "Cache-Control": "private, max-age=86400",
        "X-Accel-Buffering": "no",
    }
    status = 200
    if "Range" in kwargs and resp.get("ContentRange"):
        headers["Content-Range"] = resp["ContentRange"]
        status = 206

    def body():
        try:
            for chunk in resp["Body"].iter_chunks(READ_SIZE):
                yield chunk
        finally:
            resp["Body"].close()

    return status, headers, body()
