import io
import logging
import math
import os
import platform
import tempfile
from datetime import datetime

import boto3
import cv2
from PIL import Image
from watchtower import CloudWatchLogHandler

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
PREVIEW_SUFFIX = "_preview.gif"

PREVIEW_FRAMES = 12       # number of frames to extract
PREVIEW_DURATION_S = 6    # max seconds of source video to sample
PREVIEW_FPS = 6           # playback speed of output GIF
PREVIEW_WIDTH = 320       # output GIF width; height is auto-scaled

stream_name = f"video_previews_{platform.node()}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("video_previews")

_cloudwatch_handler = CloudWatchLogHandler(
    log_group_name="cron",
    stream_name=stream_name,
    boto3_client=boto3.client("logs", region_name=os.environ.get("AWS_REGION", "us-east-1")),
)
_cloudwatch_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(_cloudwatch_handler)


def _s3_client():
    return boto3.client("s3")


def list_bucket_objects(s3, bucket):
    """Return {key: LastModified} for every object in the bucket."""
    objects = {}
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            objects[obj["Key"]] = obj["LastModified"]
    return objects


def preview_key_for(video_key):
    """Derive the S3 key of the preview GIF for a given video key."""
    dot = video_key.rfind(".")
    base = video_key[:dot] if dot != -1 else video_key
    return base + PREVIEW_SUFFIX


def extract_frames(video_path, n_frames, max_seconds):
    """Return a list of RGB numpy arrays sampled evenly from the first max_seconds."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sample_end = min(total_frames, int(fps * max_seconds))
    if sample_end < 1:
        cap.release()
        return []

    indices = [int(i * sample_end / n_frames) for i in range(n_frames)]
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    cap.release()
    return frames


def frames_to_gif(frames, width, frame_duration_ms):
    """Convert RGB numpy frames into an animated GIF, returned as a BytesIO."""
    pil_frames = []
    for frame in frames:
        h, w = frame.shape[:2]
        new_h = max(1, math.ceil(h * width / w))
        img = Image.fromarray(frame).resize((width, new_h), Image.LANCZOS)
        pil_frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))

    buf = io.BytesIO()
    pil_frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=pil_frames[1:],
        loop=0,
        duration=frame_duration_ms,
        optimize=True,
    )
    buf.seek(0)
    return buf


def generate_and_upload(s3, bucket, video_key):
    """Download video, build preview GIF, upload to S3. Returns preview S3 key."""
    ext = os.path.splitext(video_key)[1].lower() or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name
    try:
        logger.info("Downloading s3://%s/%s", bucket, video_key)
        s3.download_file(bucket, video_key, tmp_path)

        frames = extract_frames(tmp_path, PREVIEW_FRAMES, PREVIEW_DURATION_S)
        if not frames:
            raise RuntimeError(f"No frames could be extracted from {video_key}")

        frame_duration_ms = int(1000 / PREVIEW_FPS)
        gif_buf = frames_to_gif(frames, PREVIEW_WIDTH, frame_duration_ms)

        preview_key = preview_key_for(video_key)
        logger.info("Uploading preview → s3://%s/%s", bucket, preview_key)
        s3.upload_fileobj(gif_buf, bucket, preview_key, ExtraArgs={"ContentType": "image/gif"})
        return preview_key
    finally:
        os.unlink(tmp_path)


def handler(event, context):
    bucket = os.environ.get("CDN_BUCKET_NAME", "cmh.sh")
    logger.info("=== generate_video_previews starting, bucket=%s ===", bucket)

    s3 = _s3_client()
    all_objects = list_bucket_objects(s3, bucket)

    # Partition: source videos vs existing preview GIFs
    videos = {
        k: v for k, v in all_objects.items()
        if os.path.splitext(k)[1].lower() in VIDEO_EXTENSIONS
        and not k.endswith(PREVIEW_SUFFIX)
    }
    previews = {k: v for k, v in all_objects.items() if k.endswith(PREVIEW_SUFFIX)}

    created = updated = deleted = 0
    errors = []

    # Create / update
    for video_key, video_mtime in videos.items():
        preview_key = preview_key_for(video_key)
        already_exists = preview_key in previews

        if already_exists and previews[preview_key] >= video_mtime:
            logger.debug("Preview up to date for %s", video_key)
            continue

        action = "Updating" if already_exists else "Creating"
        logger.info("%s preview for %s", action, video_key)
        try:
            generate_and_upload(s3, bucket, video_key)
            if already_exists:
                updated += 1
            else:
                created += 1
        except Exception:
            logger.exception("Failed to generate preview for %s", video_key)
            errors.append(video_key)

    # Delete orphaned previews whose source video no longer exists
    expected_previews = {preview_key_for(vk) for vk in videos}
    for preview_key in list(previews.keys()):
        if preview_key not in expected_previews:
            logger.info("Deleting orphaned preview %s", preview_key)
            try:
                s3.delete_object(Bucket=bucket, Key=preview_key)
                deleted += 1
            except Exception:
                logger.exception("Failed to delete orphaned preview %s", preview_key)
                errors.append(preview_key)

    logger.info(
        "=== generate_video_previews done: created=%d updated=%d deleted=%d errors=%d ===",
        created, updated, deleted, len(errors),
    )
    return {"created": created, "updated": updated, "deleted": deleted, "errors": errors}


if __name__ == "__main__":
    handler(None, None)