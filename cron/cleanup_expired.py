import json
import logging
import os
import urllib.request
import urllib.error

import boto3
import pyotp

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
        body = json.loads(e.read())
        raise RuntimeError(f"Login failed: {body.get('message', e.code)}")

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
        body = json.loads(e.read())
        raise RuntimeError(f"Cleanup failed: {body.get('message', e.code)}")


def handler(event, context):
    base_url = os.environ["APP_BASE_URL"].rstrip("/")

    secrets = get_secrets()
    api_key_salt = secrets["VACUUMAPIKEYSALT"]
    otp_secret = secrets["OTS_SECRET"]

    logger.info("Logging in to %s", base_url)
    token = api_login(base_url, api_key_salt, otp_secret)
    logger.info("Login successful, running cleanup")

    result = run_cleanup(base_url, token)
    deleted = result.get("deleted", [])
    failed = result.get("failed", [])

    logger.info("Cleanup complete. Deleted %d file(s), failed %d.", len(deleted), len(failed))
    if deleted:
        logger.info("Deleted: %s", deleted)
    if failed:
        logger.error("Failed to delete: %s", failed)

    return {
        "statusCode": 200,
        "body": result,
    }

if __name__ == "__main__":
    handler(None, None)
