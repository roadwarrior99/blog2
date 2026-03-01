import os
import re
import json
import sqlite3
import datetime
import boto3
import pyotp
from Crypto.Hash import SHA512
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver

logger = Logger()
# Strip the stage name + /baas prefix (e.g. /production/baas or just /baas)
# so routes see clean paths like /posts, /tags, etc.
app = APIGatewayHttpResolver(strip_prefixes=[re.compile(r"^/[^/]+/baas"), "/baas"])

DB_PATH = os.environ.get("DB_PATH", "/mnt/efs/data/vacuumflask.db")

_secrets = None


def get_secrets():
    global _secrets
    if _secrets is None:
        client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        response = client.get_secret_value(SecretId=os.environ.get("AWS_SECRET_ID"))
        _secrets = json.loads(response["SecretString"])
        logger.info("Secrets loaded from Secrets Manager")
    return _secrets


def get_db():
    return sqlite3.connect(DB_PATH)


# --- Auth helpers (mirrors hash.py and objects.py User) ---

def _hash(input_str, salt):
    """SHA512/256 hash — identical to hash.py"""
    h = SHA512.new(truncate="256")
    h.update(bytes(input_str + salt, "utf-8"))
    return h.hexdigest()


def _generate_token(username, secrets):
    """Hour-windowed token using the same key material as objects.py User.get_apikey()"""
    hour_str = datetime.datetime.utcnow().strftime("%Y%m%d%H")
    raw = secrets["VACUUMAPIKEYSALT"] + username + hour_str + secrets["VACUUMAPIKEYSALT"]
    return _hash(raw, secrets["VACUUMSALT"])


def _validate_token(presented, secrets):
    """Accept tokens from the current hour or the previous hour (boundary tolerance)."""
    username = secrets["VACUUMROOTUSER"]
    now = datetime.datetime.utcnow()
    for delta in [0, -1]:
        hour_str = (now + datetime.timedelta(hours=delta)).strftime("%Y%m%d%H")
        raw = secrets["VACUUMAPIKEYSALT"] + username + hour_str + secrets["VACUUMAPIKEYSALT"]
        if presented == _hash(raw, secrets["VACUUMSALT"]):
            return True
    return False


def require_auth():
    """Returns (error_dict, status_code) on failure, (None, None) on success."""
    auth_header = app.current_event.get_header_value("Authorization") or ""
    if not auth_header.startswith("Bearer "):
        return {"error": "Authorization header with Bearer token required"}, 401
    token = auth_header[7:]
    if not _validate_token(token, get_secrets()):
        logger.warning("Invalid or expired API key presented")
        return {"error": "Invalid or expired API key"}, 401
    return None, None


# --- DB helpers ---

def post_to_dict(r):
    return {
        "id": r[0],
        "subject": r[1],
        "date": r[2],
        "rss_description": r[3],
        "seo_keywords": r[4],
        "body": r[5],
        "old_id": r[6] if len(r) > 6 else None,
    }


def save_seo_terms(conn, seo_raw, post_id):
    """Port of objects.blog_post.save_seo_terms() — keeps tags table in sync."""
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM tags WHERE enabled = 1")
    tag_ids = {row[1]: row[0] for row in cur.fetchall()}

    tag_ids_in_use = []
    for term in seo_raw.split(","):
        term = term.lower().strip()
        if not term:
            continue
        if term not in tag_ids:
            cur.execute("INSERT INTO tags(name) VALUES (?)", [term])
            cur.execute("SELECT max(id) FROM tags")
            tag_ids[term] = cur.fetchone()[0]

        tag_id = tag_ids[term]
        tag_ids_in_use.append(tag_id)

        cur.execute("SELECT id FROM post_tags WHERE post_id=? AND tag_id=?", (post_id, tag_id))
        if not cur.fetchone():
            cur.execute("INSERT INTO post_tags(post_id, tag_id) VALUES (?, ?)", (post_id, tag_id))

    if tag_ids_in_use:
        placeholders = ",".join(map(str, tag_ids_in_use))
        cur.execute(
            f"DELETE FROM post_tags WHERE post_id=? AND tag_id NOT IN ({placeholders})",
            [post_id],
        )

    cur.execute("DELETE FROM tags WHERE id NOT IN (SELECT tag_id FROM post_tags)")
    cur.close()


# --- Public routes ---

@app.get("/posts")
def list_posts():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM post ORDER BY id DESC")
    results = cur.fetchall()
    cur.close()
    conn.close()
    return [post_to_dict(r) for r in results]


@app.get("/posts/old/<old_id>")
def get_post_by_old_id(old_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM post WHERE old_id = ?", [old_id])
    r = cur.fetchone()
    cur.close()
    conn.close()
    if not r:
        return {"error": "Post not found"}, 404
    return post_to_dict(r)


@app.get("/posts/<post_id>")
def get_post(post_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM post WHERE id = ?", [post_id])
    r = cur.fetchone()
    cur.close()
    conn.close()
    if not r:
        return {"error": "Post not found"}, 404
    return post_to_dict(r)


@app.get("/tags")
def get_tags():
    conn = get_db()
    sql = """
    SELECT t.name, count(pt.id)
    FROM tags t
    LEFT JOIN post_tags pt ON pt.tag_id = t.id
    GROUP BY t.name
    HAVING t.enabled = 1 AND count(pt.id) > 0
    """
    cur = conn.cursor()
    cur.execute(sql)
    results = cur.fetchall()
    cur.close()
    conn.close()
    tags = {r[0]: r[1] for r in results}
    max_count = max(tags.values()) if tags else 0
    min_count = min(tags.values()) if tags else 0
    return {
        "tags": tags,
        "max_font_size": 50,
        "min_font_size": 10,
        "max_count": max_count,
        "min_count": min_count,
    }


@app.get("/tags/<name>/posts")
def get_posts_by_tag(name):
    conn = get_db()
    sql = """
    SELECT p.id, p.old_id, p.date, p.rss_description, p.seo_keywords, p.body, p.subject
    FROM post p
    INNER JOIN post_tags pt ON pt.post_id = p.id
    INNER JOIN tags t ON t.id = pt.tag_id
    WHERE t.name LIKE ? AND t.enabled = 1
    ORDER BY p.id DESC
    """
    cur = conn.cursor()
    cur.execute(sql, [name])
    results = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": r[0],
            "old_id": r[1],
            "date": r[2],
            "rss_description": r[3],
            "seo_keywords": r[4],
            "body": r[5],
            "subject": r[6],
        }
        for r in results
    ]


# --- Auth route ---

@app.post("/login")
def login():
    body = app.current_event.json_body or {}
    username = body.get("username", "")
    password = body.get("password", "")
    otp = body.get("otp", "")

    if not (username and password and otp):
        return {"error": "username, password, and otp are required"}, 400

    secrets = get_secrets()
    pwd_hash = _hash(password, secrets["VACUUMSALT"])
    totp = pyotp.TOTP(secrets["OTS_SECRET"])

    if (username == secrets["VACUUMROOTUSER"]
            and pwd_hash == secrets["VACUUMROOTHASH"]
            and totp.verify(otp)):
        api_key = _generate_token(username, secrets)
        expires_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat() + "Z"
        logger.info(f"Successful login for user: {username}")
        return {"api_key": api_key, "expires_at": expires_at}

    logger.warning(f"Failed login attempt for user: {username}")
    return {"error": "Invalid credentials"}, 401


# --- Protected admin routes ---

@app.post("/posts")
def create_post():
    err, status = require_auth()
    if err:
        return err, status

    body = app.current_event.json_body or {}
    for field in ["subject", "date", "rss_description", "seo_keywords", "body"]:
        if field not in body:
            return {"error": f"Missing required field: {field}"}, 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO post(subject, date, rss_description, seo_keywords, body) VALUES (?, ?, ?, ?, ?)",
        [body["subject"], body["date"], body["rss_description"], body["seo_keywords"], body["body"]],
    )
    cur.execute("SELECT max(id) FROM post")
    new_id = cur.fetchone()[0]
    save_seo_terms(conn, body["seo_keywords"], new_id)
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Post created with id: {new_id}")
    return {"id": new_id, "message": "Post created"}, 201


@app.put("/posts/<post_id>")
def update_post(post_id):
    err, status = require_auth()
    if err:
        return err, status

    body = app.current_event.json_body or {}
    for field in ["subject", "date", "rss_description", "seo_keywords", "body"]:
        if field not in body:
            return {"error": f"Missing required field: {field}"}, 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE post SET subject=?, date=?, rss_description=?, seo_keywords=?, body=? WHERE id=?",
        [body["subject"], body["date"], body["rss_description"], body["seo_keywords"], body["body"], post_id],
    )
    if cur.rowcount == 0:
        cur.close()
        conn.close()
        return {"error": "Post not found"}, 404
    save_seo_terms(conn, body["seo_keywords"], int(post_id))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Post {post_id} updated")
    return {"message": "Post updated"}


@app.delete("/posts/<post_id>")
def delete_post(post_id):
    err, status = require_auth()
    if err:
        return err, status

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM post_tags WHERE post_id=?", [post_id])
    cur.execute("DELETE FROM post WHERE id=?", [post_id])
    if cur.rowcount == 0:
        cur.close()
        conn.close()
        return {"error": "Post not found"}, 404
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Post {post_id} deleted")
    return {"message": "Post deleted"}


@logger.inject_lambda_context
def lambda_handler(event, context):
    logger.info(event)
    return app.resolve(event, context)
