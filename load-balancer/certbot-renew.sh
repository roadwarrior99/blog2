#!/bin/bash
mkdir -p /var/www/certbot

ALERT_EMAIL="${ALERT_EMAIL:-coloncancer@gmail.com}"
AWS_REGION="${AWS_REGION:-us-east-1}"

OUTPUT=$(certbot renew --webroot -w /var/www/certbot --quiet 2>&1)
STATUS=$?

if [ $STATUS -eq 0 ]; then
    nginx -s reload
else
    echo "$OUTPUT" | python3 -c "
import json, sys
json.dump({
    'Subject': {'Data': 'cmh.sh load balancer: certbot renewal failed'},
    'Body': {'Text': {'Data': sys.stdin.read()}},
}, open('/tmp/ses-message.json', 'w'))
"
    aws ses send-email \
        --region "$AWS_REGION" \
        --from "$ALERT_EMAIL" \
        --destination "ToAddresses=$ALERT_EMAIL" \
        --message file:///tmp/ses-message.json \
        || echo "WARNING: certbot renewal failed AND SES alert failed to send"
fi