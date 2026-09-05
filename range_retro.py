"""
range_retro.py — build a monthly "range retrospective" ("Paper Punches") blog post
from a zip of iPhone photos.

Pipeline (runs in a background thread, progress tracked in the ``range_job`` table):

  1. Unzip the upload.
  2. For every image (HEIC / JPG / PNG):
       - honour EXIF orientation, then re-encode to a web-friendly JPEG with
         *all* metadata (including GPS) dropped.
       - build a smaller thumbnail.
       - pull the capture timestamp from EXIF so we can order the timeline.
       - ask AWS Rekognition whether the frame contains a firearm.
       - upload the web JPEG + thumbnail to the public CDN bucket.
  3. Write the ordered manifest back to the job row.

The Flask side then shows a commentary form (firearm photos flagged) and, on
publish, assembles the post body: one chronological slideshow followed by a
write-up section per firearm photo.
"""

import io
import json
import logging
import os
import sqlite3
import tempfile
import threading
import zipfile
from datetime import datetime

import boto3
import pillow_heif
from PIL import Image, ImageOps

pillow_heif.register_heif_opener()

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".heic", ".heif", ".jpg", ".jpeg", ".png"}

WEB_MAX_EDGE = 2200          # longest edge of the published image
THUMB_MAX_EDGE = 600         # longest edge of the grid thumbnail
DETECT_MAX_EDGE = 1400       # frame sent to Rekognition (keeps us < 5 MB limit)
JPEG_QUALITY = 85

# Rekognition labels (lower-cased) that mean "there is a gun in this picture".
FIREARM_LABELS = {
    "gun", "weapon", "handgun", "rifle", "shotgun", "firearm",
    "pistol", "revolver", "machine gun", "ammunition",
}

CDN_PUBLIC_BASE = os.environ.get("CDN_PUBLIC_BASE", "https://pub.cmh.sh/").rstrip("/") + "/"


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────
def ensure_tables(db_path):
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS range_job (
            id          TEXT PRIMARY KEY,
            status      TEXT NOT NULL,          -- pending | processing | done | error
            year        INTEGER NOT NULL,
            month       INTEGER NOT NULL,
            created_at  TEXT NOT NULL,
            message     TEXT DEFAULT '',
            total       INTEGER DEFAULT 0,
            processed   INTEGER DEFAULT 0,
            manifest    TEXT DEFAULT '[]',      -- JSON list of photo dicts
            post_id     INTEGER                 -- set once published
        )
    """)
    conn.commit()
    conn.close()


def create_job(db_path, job_id, year, month):
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute(
        "INSERT INTO range_job (id, status, year, month, created_at) VALUES (?, 'pending', ?, ?, ?)",
        [job_id, year, month, datetime.utcnow().isoformat()],
    )
    conn.commit()
    conn.close()


def get_job(db_path, job_id):
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM range_job WHERE id = ?", [job_id])
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    job = dict(row)
    job["manifest"] = json.loads(job["manifest"] or "[]")
    return job


def _update_job(db_path, job_id, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute(f"UPDATE range_job SET {cols} WHERE id = ?", [*fields.values(), job_id])
    conn.commit()
    conn.close()


def save_manifest(db_path, job_id, manifest):
    _update_job(db_path, job_id, manifest=json.dumps(manifest))


def mark_published(db_path, job_id, post_id):
    _update_job(db_path, job_id, post_id=post_id)


# ─────────────────────────────────────────────────────────────────────────────
# Image processing
# ─────────────────────────────────────────────────────────────────────────────
def _exif_datetime(img):
    """Return the capture time as an ISO string, or None."""
    try:
        exif = img.getexif()
    except Exception:
        return None
    if not exif:
        return None

    raw = None
    # DateTimeOriginal / DateTimeDigitized live in the Exif sub-IFD (0x8769);
    # DateTime (0x0132) is on the root IFD.
    try:
        sub = exif.get_ifd(0x8769)
        raw = sub.get(0x9003) or sub.get(0x9004)
    except Exception:
        pass
    raw = raw or exif.get(0x0132)
    if not raw:
        return None

    raw = str(raw).strip()
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S%z"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=None).isoformat()
        except ValueError:
            continue
    return None


def _has_gps(img):
    try:
        exif = img.getexif()
        gps = exif.get_ifd(0x8825)
        return bool(gps)
    except Exception:
        return False


def _resize(img, max_edge):
    w, h = img.size
    if max(w, h) <= max_edge:
        return img
    scale = max_edge / float(max(w, h))
    return img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)


def _to_jpeg_bytes(img, max_edge):
    """Flatten to RGB, resize, and encode as a metadata-free JPEG."""
    frame = ImageOps.exif_transpose(img)          # bake in orientation
    if frame.mode not in ("RGB", "L"):
        frame = frame.convert("RGB")
    frame = _resize(frame, max_edge)
    buf = io.BytesIO()
    # No exif=, no icc_profile — nothing identifying (incl. GPS) survives.
    frame.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# AWS
# ─────────────────────────────────────────────────────────────────────────────
def _rekognition_client():
    return boto3.client("rekognition", region_name=os.environ.get("AWS_REGION"))


def _s3_client():
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION"))


def detect_firearm(rek, jpeg_bytes):
    """Return (has_firearm, [matching label names])."""
    try:
        resp = rek.detect_labels(Image={"Bytes": jpeg_bytes}, MaxLabels=40, MinConfidence=55)
    except Exception:
        logger.exception("Rekognition detect_labels failed; treating frame as no-firearm")
        return False, []
    hits = []
    for label in resp.get("Labels", []):
        name = label.get("Name", "")
        if name.lower() in FIREARM_LABELS:
            hits.append(name)
    return bool(hits), hits


def _upload(s3, bucket, key, data):
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType="image/jpeg")
    return CDN_PUBLIC_BASE + key


# ─────────────────────────────────────────────────────────────────────────────
# Worker
# ─────────────────────────────────────────────────────────────────────────────
def _iter_zip_images(zf):
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename
        base = os.path.basename(name)
        if not base or base.startswith(".") or "__MACOSX" in name:
            continue
        if os.path.splitext(base)[1].lower() in IMAGE_EXTENSIONS:
            yield info, base


def process_zip(db_path, job_id, zip_path):
    """Run the whole pipeline. Intended to be the target of a background thread."""
    bucket = os.environ.get("CDN_BUCKET_NAME")
    job = get_job(db_path, job_id)
    prefix = f"paper-punches/{job['year']:04d}-{job['month']:02d}/"

    try:
        _update_job(db_path, job_id, status="processing", message="Reading archive…")
        rek = _rekognition_client()
        s3 = _s3_client()
        manifest = []

        with zipfile.ZipFile(zip_path) as zf:
            entries = list(_iter_zip_images(zf))
            total = len(entries)
            _update_job(db_path, job_id, total=total)
            if total == 0:
                raise RuntimeError("No HEIC/JPG/PNG images found in the archive.")

            for idx, (info, base) in enumerate(entries, start=1):
                stem = os.path.splitext(base)[0]
                logger.info("range_retro %s: processing %s (%d/%d)", job_id, base, idx, total)
                try:
                    with zf.open(info) as fh:
                        img = Image.open(io.BytesIO(fh.read()))
                        img.load()

                    taken_at = _exif_datetime(img)
                    had_gps = _has_gps(img)

                    web_jpeg = _to_jpeg_bytes(img, WEB_MAX_EDGE)
                    thumb_jpeg = _to_jpeg_bytes(img, THUMB_MAX_EDGE)
                    detect_jpeg = _to_jpeg_bytes(img, DETECT_MAX_EDGE)

                    has_firearm, labels = detect_firearm(rek, detect_jpeg)

                    key = f"{prefix}{stem}.jpg"
                    thumb_key = f"{prefix}{stem}_thumb.jpg"
                    url = _upload(s3, bucket, key, web_jpeg)
                    thumb_url = _upload(s3, bucket, thumb_key, thumb_jpeg)

                    manifest.append({
                        "filename": f"{stem}.jpg",
                        "key": key,
                        "thumb_key": thumb_key,
                        "url": url,
                        "thumb_url": thumb_url,
                        "taken_at": taken_at,
                        "had_gps": had_gps,
                        "has_firearm": has_firearm,
                        "labels": labels,
                        "commentary": "",
                    })
                except Exception:
                    logger.exception("range_retro %s: failed on %s", job_id, base)

                _update_job(db_path, job_id, processed=idx)
                save_manifest(db_path, job_id, _order(manifest))

        if not manifest:
            raise RuntimeError("Every image in the archive failed to process.")

        manifest = _order(manifest)
        save_manifest(db_path, job_id, manifest)
        firearm_count = sum(1 for m in manifest if m["has_firearm"])
        _update_job(
            db_path, job_id, status="done",
            message=f"{len(manifest)} photos ready · {firearm_count} with a firearm detected",
        )
        logger.info("range_retro %s: done (%d photos)", job_id, len(manifest))
    except Exception as e:
        logger.exception("range_retro %s: aborted", job_id)
        _update_job(db_path, job_id, status="error", message=str(e))
    finally:
        try:
            os.unlink(zip_path)
        except OSError:
            pass


def _order(manifest):
    """Chronological where we have a timestamp; the rest fall to the end by name."""
    return sorted(
        manifest,
        key=lambda m: (m["taken_at"] is None, m["taken_at"] or "", m["filename"]),
    )


def start_job(db_path, job_id, zip_path):
    t = threading.Thread(target=process_zip, args=(db_path, job_id, zip_path), daemon=True)
    t.start()
    return t


# ─────────────────────────────────────────────────────────────────────────────
# Post assembly
# ─────────────────────────────────────────────────────────────────────────────
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def _fmt_caption(iso):
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    return dt.strftime("%b %-d, %-I:%M %p")


def _slideshow_html(manifest):
    slides = []
    for i, m in enumerate(manifest):
        caption = _fmt_caption(m["taken_at"])
        cap_div = (
            f'<div style="position:absolute;bottom:0;left:0;right:0;'
            f'background:linear-gradient(transparent,rgba(0,0,0,.7));color:#eee;'
            f'font-size:.8rem;text-align:center;padding:1.2rem 1rem .6rem;">{caption}</div>'
            if caption else ""
        )
        slides.append(
            f'    <div class="ss-slide" style="position:absolute;inset:0;'
            f'opacity:{1 if i == 0 else 0};transition:opacity .7s ease;">\n'
            f'      <img src="{m["url"]}" alt="{caption or m["filename"]}" '
            f'style="width:100%;height:100%;object-fit:contain;display:block;">\n'
            f'{cap_div}\n    </div>'
        )
    slides_html = "\n".join(slides)
    btn = (
        "position:absolute;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.5);"
        "border:1px solid #444;color:#eee;font-size:1.4rem;width:2.4rem;height:2.4rem;"
        "cursor:pointer;z-index:10;"
    )
    return (
        '<div class="slideshow" data-interval="4500" '
        'style="position:relative;width:100%;max-width:860px;margin:2rem auto;">\n'
        '  <div class="ss-wrap" style="position:relative;width:100%;aspect-ratio:4/3;'
        'overflow:hidden;background:#000;border:1px solid #333;border-radius:8px;">\n'
        f'{slides_html}\n'
        f'    <button data-ss-dir="-1" style="{btn}left:.5rem;">‹</button>\n'
        f'    <button data-ss-dir="1" style="{btn}right:.5rem;">›</button>\n'
        '  </div>\n'
        '  <div style="height:3px;background:#333;margin-top:.5rem;border-radius:2px;overflow:hidden;">\n'
        '    <div class="ss-bar" style="height:100%;background:#888;width:0;"></div>\n'
        '  </div>\n'
        '  <div class="ss-dots" style="display:flex;justify-content:center;gap:.5rem;margin-top:.5rem;"></div>\n'
        '</div>'
    )


def build_post_body(manifest, intro_html):
    """Assemble the final post body: intro + timeline slideshow + rental write-ups."""
    parts = []
    if intro_html and intro_html.strip():
        parts.append(intro_html.strip())

    parts.append(_slideshow_html(manifest))

    writeups = [m for m in manifest if m["has_firearm"] and m.get("commentary", "").strip()]
    if writeups:
        parts.append('<h2>The rentals</h2>')
        for m in writeups:
            caption = _fmt_caption(m["taken_at"])
            when = f'<p style="color:#64748b;font-size:.85rem;margin:0 0 .4rem;">{caption}</p>' if caption else ""
            parts.append(
                '<div style="margin:1.6rem 0;">\n'
                f'  <img src="{m["url"]}" alt="{caption or m["filename"]}" '
                'style="width:100%;max-width:860px;border-radius:8px;display:block;margin:0 auto 0.6rem;">\n'
                f'  {when}\n'
                f'  {m["commentary"].strip()}\n'
                '</div>'
            )
    return "\n\n".join(parts)


def default_subject(year, month):
    return f"Paper Punches — {MONTHS[month]} {year}"


def default_date(manifest, year, month):
    for m in manifest:
        if m["taken_at"]:
            return m["taken_at"][:10]
    return f"{year:04d}-{month:02d}-01"