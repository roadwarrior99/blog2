#!/bin/bash
curl -X POST http://localhost:5000/blogpost \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "subject=Sample Subject" \
     -d "date=07/04/2024" \
     -d "rss_description=This is a sample RSS description" \
     -d "body=This is the body of the blog post" \
     -d "seo_keywords=sample,blog,post"

