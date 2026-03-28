#!/bin/bash
set -e

BUCKET="blog.cmh.sh"
PROFILE="terraform"
REGION="us-east-1"
BASE_DIR="$(dirname "$0")/blog-post-pages"

if [ ! -d "$BASE_DIR/post" ]; then
  echo "Pages not found. Run first: python3 baas/generate-post-pages.py"
  exit 1
fi

# Files are extension-less HTML — must set content-type explicitly
echo "Uploading post pages to s3://$BUCKET/post/ ..."
aws s3 sync "$BASE_DIR/post" "s3://$BUCKET/post/" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --content-type "text/html" \
  --cache-control "max-age=300" \
  --exclude "*.DS_Store"

echo "Uploading tag pages to s3://$BUCKET/tag/ ..."
aws s3 sync "$BASE_DIR/tag" "s3://$BUCKET/tag/" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --content-type "text/html" \
  --cache-control "max-age=300" \
  --exclude "*.DS_Store"

echo "Done. https://$BUCKET/post/<id>  https://$BUCKET/tag/<name>"
date
