import html
import sqlite3
import os

from mcp.server.fastmcp import FastMCP

DB = os.environ.get(
    "MCP_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "vacuumflask.db")
)

mcp = FastMCP("while(motivation <= 0) blog")


@mcp.resource("blog://posts")
def list_posts() -> str:
    """List all blog posts with id, title, date, and summary."""
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, subject, date, rss_description FROM post ORDER BY id DESC"
    ).fetchall()
    conn.close()
    if not rows:
        return "No posts found."
    return "\n\n".join(
        f"[{r[0]}] {r[1]} ({r[2]})\n{r[3]}" for r in rows
    )


@mcp.resource("blog://post/{post_id}")
def get_post(post_id: int) -> str:
    """Get the full content of a single blog post by id."""
    conn = sqlite3.connect(DB)
    row = conn.execute(
        "SELECT subject, date, rss_description, body FROM post WHERE id=?",
        [post_id]
    ).fetchone()
    conn.close()
    if not row:
        return f"Post {post_id} not found."
    subject, date, summary, body = row
    return f"# {subject}\n**{date}**\n\n{summary}\n\n{html.unescape(body)}"


@mcp.resource("blog://tags")
def list_tags() -> str:
    """List all active tags with their post counts."""
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT t.name, COUNT(pt.id) AS post_count
        FROM tags t
        LEFT JOIN post_tags pt ON pt.tag_id = t.id
        WHERE t.enabled = 1
        GROUP BY t.name
        HAVING post_count > 0
        ORDER BY post_count DESC
    """).fetchall()
    conn.close()
    if not rows:
        return "No tags found."
    return "\n".join(f"{r[0]} ({r[1]} posts)" for r in rows)


@mcp.tool()
def search_posts(query: str) -> str:
    """
    Search blog posts by keyword across title and body.

    Args:
        query: The keyword or phrase to search for.
    """
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        """SELECT id, subject, date, rss_description FROM post
           WHERE subject LIKE ? OR body LIKE ?
           ORDER BY id DESC""",
        [f"%{query}%", f"%{query}%"]
    ).fetchall()
    conn.close()
    if not rows:
        return f"No posts found matching '{query}'."
    return "\n\n".join(
        f"[{r[0]}] {r[1]} ({r[2]})\n{r[3]}" for r in rows
    )


@mcp.tool()
def get_posts_by_tag(tag: str) -> str:
    """
    Get all blog posts for a given tag.

    Args:
        tag: The tag name to filter by.
    """
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT p.id, p.subject, p.date, p.rss_description
        FROM post p
        JOIN post_tags pt ON pt.post_id = p.id
        JOIN tags t ON t.id = pt.tag_id
        WHERE t.name LIKE ? AND t.enabled = 1
        ORDER BY p.id DESC
    """, [tag]).fetchall()
    conn.close()
    if not rows:
        return f"No posts found for tag '{tag}'."
    return "\n\n".join(
        f"[{r[0]}] {r[1]} ({r[2]})\n{r[3]}" for r in rows
    )


@mcp.tool()
def get_recent_posts(count: int = 5) -> str:
    """
    Get the most recent blog posts.

    Args:
        count: Number of posts to return (default 5, max 20).
    """
    count = min(count, 20)
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, subject, date, rss_description FROM post ORDER BY id DESC LIMIT ?",
        [count]
    ).fetchall()
    conn.close()
    if not rows:
        return "No posts found."
    return "\n\n".join(
        f"[{r[0]}] {r[1]} ({r[2]})\n{r[3]}" for r in rows
    )


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        import uvicorn
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8001"))
        uvicorn.run(mcp.sse_app(), host=host, port=port)
    else:
        mcp.run()