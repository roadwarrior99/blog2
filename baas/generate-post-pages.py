#!/usr/bin/env python3
"""
Generate static HTML pages for every post and tag in the DB:
  blog-post-pages/post/<id>        → https://blog.cmh.sh/post/<id>
  blog-post-pages/tag/<name>       → https://blog.cmh.sh/tag/<name>

Files are extension-less so S3 serves them at the exact URL with
Content-Type: text/html (set explicitly in ship-blog-posts.sh).
"""

import sqlite3
import html
import os

DB_PATH   = os.path.join(os.path.dirname(__file__), '..', 'data', 'vacuumflask.db')
BASE_DIR  = os.path.join(os.path.dirname(__file__), 'blog-post-pages')
OUT_DIR   = os.path.join(BASE_DIR, 'post')
TAG_DIR   = os.path.join(BASE_DIR, 'tag')
BASE_URL  = 'https://blog.cmh.sh'
SPA_URL   = 'https://baas.cmh.sh/index.html'


def html_decode(s):
    """Mirror the JS htmlDecode() — unescape entities then normalize smart quotes."""
    if not s:
        return ''
    s = html.unescape(s)
    s = s.replace('\u201c', '"').replace('\u201d', '"')
    s = s.replace('\u2018', "'").replace('\u2019', "'")
    return s


def esc(s):
    return html.escape(str(s or ''), quote=True)


def fmt_date(d):
    return str(d or '')[:10]


def render_page(post_id, subject, date, description, keywords, body):
    kw_meta   = f'<meta name="keywords" content="{esc(keywords)}">\n  ' if keywords else ''
    desc_meta = f'<meta name="description" content="{esc(description)}">\n  ' if description else ''
    canonical = f'{BASE_URL}/post/{post_id}'
    tag_chips = ''
    if keywords:
        chips = []
        for t in keywords.split(','):
            t = t.strip()
            if t:
                chips.append(
                    f'<a href="{BASE_URL}/tag/{esc(t)}" '
                    f'style="display:inline-block;padding:3px 9px;background:#e0f0ff;'
                    f'border-radius:20px;color:#005f99;font-size:0.8rem;'
                    f'text-decoration:none;border:1px solid #b0d8f5;margin:2px">'
                    f'{esc(t)}</a>'
                )
        tag_chips = ' '.join(chips)

    decoded_body = html_decode(body)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(subject)} — cmh.sh</title>
  {desc_meta}{kw_meta}<link rel="canonical" href="{canonical}">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f0f4f8; color: #1a1a2e; line-height: 1.6;
    }}
    header {{
      background: #005f99; color: white; padding: 12px 20px;
      display: flex; align-items: center; gap: 16px;
    }}
    header a {{ color: white; text-decoration: none; font-size: 0.9rem; opacity: .8; }}
    header a:hover {{ opacity: 1; }}
    .container {{ max-width: 820px; margin: 32px auto; padding: 0 16px; }}
    .post-full {{
      background: white; border-radius: 10px; padding: 28px 32px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.09);
    }}
    h1 {{ font-size: 1.6rem; margin: 0 0 6px; color: #005f99; }}
    .meta {{ font-size: 0.8rem; color: #777; margin-bottom: 18px; }}
    .body {{ font-size: 0.97rem; line-height: 1.7; }}
    .body img {{ max-width: 100%; height: auto; border-radius: 4px; }}
    .body pre {{ overflow-x: auto; background: #f4f4f4; border-radius: 6px; padding: 14px; }}
    .body p {{ margin: 0 0 12px; }}
    .body h2, .body h3 {{ margin: 20px 0 8px; }}
    .tags {{ margin-top: 20px; }}
    .spa-link {{
      display: inline-block; margin-top: 24px;
      padding: 8px 18px; background: #005f99; color: white;
      border-radius: 6px; text-decoration: none; font-size: 0.9rem;
    }}
    .spa-link:hover {{ background: #004d80; }}
    footer {{
      text-align: center; padding: 24px 16px; font-size: 0.8rem; color: #999;
    }}
  </style>
</head>
<body>
  <header>
    <strong>cmh.sh</strong>
    <a href="{SPA_URL}">&#8592; All posts</a>
  </header>
  <div class="container">
    <article class="post-full">
      <h1>{esc(subject)}</h1>
      <div class="meta">{fmt_date(date)}</div>
      <div class="body">{decoded_body}</div>
      {f'<div class="tags">{tag_chips}</div>' if tag_chips else ''}
      <a class="spa-link" href="{SPA_URL}">&#8592; Back to all posts</a>
    </article>
  </div>
  <footer>&copy; cmh.sh</footer>
</body>
</html>
"""


def render_tag_page(tag_name, posts):
    """posts: list of (id, subject, date, rss_description)"""
    canonical = f'{BASE_URL}/tag/{esc(tag_name)}'
    rows_html = '\n'.join(
        f'<li><a href="{BASE_URL}/post/{p[0]}">{esc(p[1])}</a>'
        f'<span class="date"> — {fmt_date(p[2])}</span>'
        f'{"<p class=desc>" + esc(p[3]) + "</p>" if p[3] else ""}'
        f'</li>'
        for p in posts
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Posts tagged &#8220;{esc(tag_name)}&#8221; — cmh.sh</title>
  <meta name="description" content="Posts tagged {esc(tag_name)} on cmh.sh">
  <link rel="canonical" href="{canonical}">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f0f4f8; color: #1a1a2e; line-height: 1.6;
    }}
    header {{
      background: #005f99; color: white; padding: 12px 20px;
      display: flex; align-items: center; gap: 16px;
    }}
    header a {{ color: white; text-decoration: none; font-size: 0.9rem; opacity: .8; }}
    header a:hover {{ opacity: 1; }}
    .container {{ max-width: 820px; margin: 32px auto; padding: 0 16px; }}
    .card {{
      background: white; border-radius: 10px; padding: 28px 32px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.09);
    }}
    h1 {{ font-size: 1.4rem; margin: 0 0 20px; color: #005f99; }}
    ul {{ list-style: none; margin: 0; padding: 0; }}
    li {{ border-bottom: 1px solid #eee; padding: 12px 0; }}
    li:last-child {{ border-bottom: none; }}
    li a {{ color: #005f99; text-decoration: none; font-weight: 600; font-size: 1rem; }}
    li a:hover {{ text-decoration: underline; }}
    .date {{ font-size: 0.8rem; color: #777; }}
    .desc {{ margin: 4px 0 0; font-size: 0.88rem; color: #555; }}
    .spa-link {{
      display: inline-block; margin-top: 20px;
      padding: 8px 18px; background: #005f99; color: white;
      border-radius: 6px; text-decoration: none; font-size: 0.9rem;
    }}
    .spa-link:hover {{ background: #004d80; }}
    footer {{
      text-align: center; padding: 24px 16px; font-size: 0.8rem; color: #999;
    }}
  </style>
</head>
<body>
  <header>
    <strong>cmh.sh</strong>
    <a href="{SPA_URL}">&#8592; All posts</a>
  </header>
  <div class="container">
    <div class="card">
      <h1>Posts tagged &#8220;{esc(tag_name)}&#8221;</h1>
      <ul>{rows_html}</ul>
      <a class="spa-link" href="{SPA_URL}">&#8592; Back to all posts</a>
    </div>
  </div>
  <footer>&copy; cmh.sh</footer>
</body>
</html>
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── Post pages ────────────────────────────────────────────────────────────
    cur.execute("SELECT id, subject, date, rss_description, seo_keywords, body FROM post ORDER BY id")
    post_rows = cur.fetchall()

    os.makedirs(OUT_DIR, exist_ok=True)
    count = 0
    for row in post_rows:
        post_id, subject, date, desc, keywords, body = row
        page = render_page(post_id, subject, date, desc, keywords, body)
        with open(os.path.join(OUT_DIR, str(post_id)), 'w', encoding='utf-8') as f:
            f.write(page)
        count += 1
        print(f'  {BASE_URL}/post/{post_id}  — {subject[:60]}')
    print(f'\nGenerated {count} post pages in {OUT_DIR}')

    # ── Tag pages ─────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT t.Name, p.id, p.subject, p.date, p.rss_description
        FROM tags t
        JOIN post_tags pt ON pt.tag_id = t.id
        JOIN post p       ON p.id = pt.post_id
        ORDER BY t.Name, p.date DESC
    """)
    tag_map = {}
    for tag_name, post_id, subject, date, desc in cur.fetchall():
        tag_map.setdefault(tag_name, []).append((post_id, subject, date, desc))

    conn.close()

    os.makedirs(TAG_DIR, exist_ok=True)
    tag_count = 0
    for tag_name, posts in sorted(tag_map.items()):
        page = render_tag_page(tag_name, posts)
        # Slugify: lowercase, spaces→hyphens, keep alphanum/hyphen
        slug = tag_name.lower().replace(' ', '-')
        with open(os.path.join(TAG_DIR, slug), 'w', encoding='utf-8') as f:
            f.write(page)
        tag_count += 1
        print(f'  {BASE_URL}/tag/{slug}  ({len(posts)} posts)')
    print(f'\nGenerated {tag_count} tag pages in {TAG_DIR}')
    print('Upload with: ./baas/ship-blog-posts.sh')


if __name__ == '__main__':
    main()
