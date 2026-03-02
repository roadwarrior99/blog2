#!/usr/bin/env python3
"""
Generate static HTML pages for every post in the DB at:
  baas/front-end/post/<id>/index.html

These are served via S3/CloudFront at https://baas.cmh.sh/post/<id>/
so that Google (and old inbound links) can reach individual post pages.
"""

import sqlite3
import html
import os
import re

DB_PATH   = os.path.join(os.path.dirname(__file__), '..', 'data', 'vacuumflask.db')
OUT_DIR   = os.path.join(os.path.dirname(__file__), 'front-end', 'post')
BASE_URL  = 'https://baas.cmh.sh'
SPA_URL   = f'{BASE_URL}/index.html'


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
    canonical = f'{BASE_URL}/post/{post_id}/'
    tag_chips = ''
    if keywords:
        chips = []
        for t in keywords.split(','):
            t = t.strip()
            if t:
                chips.append(
                    f'<a href="{SPA_URL}#" '
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


def main():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("SELECT id, subject, date, rss_description, seo_keywords, body FROM post ORDER BY id")
    rows = cur.fetchall()
    conn.close()

    os.makedirs(OUT_DIR, exist_ok=True)
    count = 0
    for row in rows:
        post_id, subject, date, desc, keywords, body = row
        post_dir = os.path.join(OUT_DIR, str(post_id))
        os.makedirs(post_dir, exist_ok=True)
        page = render_page(post_id, subject, date, desc, keywords, body)
        with open(os.path.join(post_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(page)
        count += 1
        print(f'  {BASE_URL}/post/{post_id}/  — {subject[:60]}')

    print(f'\nGenerated {count} pages in {OUT_DIR}')


if __name__ == '__main__':
    main()
