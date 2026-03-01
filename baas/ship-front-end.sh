#!/bin/bash
set -e

BUCKET="baas.cmh.sh"
PROFILE="terraform"
REGION="us-east-1"
CF_DIST_ID="E1IBT9K1Z6XL4Y"
SRC_DIR="$(dirname "$0")/front-end"

echo "Deploying front-end to s3://$BUCKET ..."

aws s3 sync "$SRC_DIR" "s3://$BUCKET/" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --delete \
  --cache-control "max-age=300" \
  --exclude "*.DS_Store"

echo "Invalidating CloudFront distribution $CF_DIST_ID ..."

aws cloudfront create-invalidation \
  --profile "$PROFILE" \
  --distribution-id "$CF_DIST_ID" \
  --paths "/*" \
  --query "Invalidation.{Id:Id,Status:Status}" \
  --output table

echo "Done. https://$BUCKET/"
