#!/bin/bash

# Start cron for certbot auto-renewal
service cron start

provision_cert() {
    local domain=$1
    local dir="/etc/letsencrypt/live/$domain"
    if [ ! -f "$dir/fullchain.pem" ]; then
        echo "Generating temporary self-signed cert for $domain..."
        mkdir -p "$dir"
        openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
            -keyout "$dir/privkey.pem" \
            -out "$dir/fullchain.pem" \
            -subj "/CN=$domain" 2>/dev/null
    fi
}

get_cert() {
    local domains=$1
    local primary=$2
    local cert="/etc/letsencrypt/live/$primary/fullchain.pem"
    # If a valid non-expiring cert already exists here, keep it
    if [ -f "$cert" ] && openssl x509 -checkend 86400 -noout -in "$cert" 2>/dev/null; then
        echo "Valid cert already exists for $primary, skipping."
        return
    fi
    echo "Requesting letsencrypt cert for $domains..."
    # Remove all certbot state for this domain so it creates at the expected path
    rm -rf /etc/letsencrypt/live/$primary
    rm -rf /etc/letsencrypt/archive/$primary
    rm -f  /etc/letsencrypt/renewal/$primary.conf
    certbot certonly --webroot -w /var/www/certbot \
        $domains \
        --non-interactive --agree-tos --email admin@cmh.sh --force-renewal \
        || echo "WARNING: certbot failed for $primary — will retry on next restart"
}

# Ensure certs exist for all domains so nginx can start
provision_cert blog.cmh.sh
provision_cert cmh.sh
provision_cert colinhayes.dev

# Start nginx in background so certbot can complete the HTTP-01 challenge
nginx -g "daemon on;"

# If cert is self-signed (expires within 1 day), replace with letsencrypt certs
if openssl x509 -checkend 86400 -noout -in /etc/letsencrypt/live/blog.cmh.sh/fullchain.pem 2>/dev/null; then
    : # cert is valid for more than 1 day, skip provisioning
else
    echo "Temporary certs detected — obtaining letsencrypt certs..."
    get_cert "-d blog.cmh.sh -d blog4.cmh.sh" "blog.cmh.sh"
    get_cert "-d cmh.sh -d ots.cmh.sh" "cmh.sh"
    get_cert "-d colinhayes.dev -d blog.colinhayes.dev -d about.colinhayes.dev -d links.colinhayes.dev" "colinhayes.dev"
fi

echo "Stopping temporary nginx..."
nginx -s stop
sleep 1

# Start nginx in the foreground as the main container process
exec nginx -g "daemon off;"