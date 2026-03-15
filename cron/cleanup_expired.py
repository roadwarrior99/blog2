import json
import logging
import os
import platform
import urllib.request
import urllib.error
from datetime import datetime

import boto3
import pyotp
from watchtower import CloudWatchLogHandler

stream_name = f"cleanup_expired_{platform.node()}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cleanup_expired")

_cloudwatch_handler = CloudWatchLogHandler(
    log_group_name="cron",
    stream_name=stream_name,
    boto3_client=boto3.client("logs", region_name=os.environ.get("AWS_REGION", "us-east-1")),
)
_cloudwatch_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(_cloudwatch_handler)


def get_secrets():
    client = boto3.client("secretsmanager", region_name=os.environ["AWS_REGION"])
    response = client.get_secret_value(SecretId=os.environ["AWS_SECRET_ID"])
    return json.loads(response["SecretString"])


def api_login(base_url, api_key_salt, otp_secret):
    otp = pyotp.TOTP(otp_secret).now()
    payload = json.dumps({"api_key_salt": api_key_salt, "otp": otp}).encode()
    req = urllib.request.Request(
        f"{base_url}/api/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            msg = json.loads(raw).get("message", e.code)
        except Exception:
            msg = raw.decode(errors="replace") or f"HTTP {e.code}"
        raise RuntimeError(f"Login failed ({e.code}): {msg}")

    if not body.get("success"):
        raise RuntimeError(f"Login failed: {body.get('message')}")

    return body["token"]


def run_cleanup(base_url, token):
    req = urllib.request.Request(
        f"{base_url}/admin/cleanup_expired",
        data=b"",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            msg = json.loads(raw).get("message", e.code)
        except Exception:
            msg = raw.decode(errors="replace") or f"HTTP {e.code}"
        raise RuntimeError(f"Cleanup failed ({e.code}): {msg}")


def handler(event, context):
    logger.info("=== cleanup_expired starting ===")
    try:
        base_url = os.environ["APP_BASE_URL"].rstrip("/")
        logger.info("Target: %s", base_url)

        logger.info("Fetching secrets from Secrets Manager...")
        secrets = get_secrets()
        api_key_salt = secrets["VACUUMAPIKEYSALT"]
        otp_secret = secrets["OTS_SECRET"]
        logger.info("Secrets loaded.")

        logger.info("Logging in to %s", base_url)
        token = api_login(base_url, api_key_salt, otp_secret)
        logger.info("Login successful.")

        logger.info("Running expired media cleanup...")
        result = run_cleanup(base_url, token)
        deleted = result.get("deleted", [])
        failed = result.get("failed", [])

        logger.info("Cleanup complete. Deleted: %d  Failed: %d", len(deleted), len(failed))
        for key in deleted:
            logger.info("  Deleted: %s", key)
        for key in failed:
            logger.error("  Failed:  %s", key)

        logger.info("=== cleanup_expired finished ===")
        return {"statusCode": 200, "body": result}

    except Exception as e:
        logger.exception("cleanup_expired failed: %s", e)
        raise

if __name__ == "__main__":
    handler(None, None)
