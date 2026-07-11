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

mkdir -p /var/www/certbot

# Every hostname nginx.conf loads a cert for, one per server block. Each is
# requested independently so one unreachable domain (stale DNS, etc.) can't
# take down certs for the others sharing a cert group.
DOMAINS="blog.cmh.sh blog4.cmh.sh cmh.sh ots.cmh.sh colinhayes.dev blog.colinhayes.dev about.colinhayes.dev links.colinhayes.dev"

# Ensure a cert file exists for every domain so nginx can start even on a
# fresh volume where no real certs have been issued yet.
for domain in $DOMAINS; do
    provision_cert "$domain"
done

# Start nginx in background so certbot can complete the HTTP-01 challenge
nginx -g "daemon on;"

# get_cert no-ops per-domain when a valid cert already exists, so it's safe
# (and necessary for self-healing after a DNS fix) to attempt every domain
# on every restart rather than gating the whole batch on one domain's cert.
for domain in $DOMAINS; do
    get_cert "-d $domain" "$domain"
done

echo "Stopping temporary nginx..."
nginx -s stop
sleep 1

# Start nginx in the foreground as the main container process
exec nginx -g "daemon off;"