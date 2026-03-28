#!/bin/sh
set -e

EMAIL="${CERTBOT_EMAIL:-colin@cmh.sh}"
WEBROOT="/var/www/certbot"

needs_cert() {
    [ ! -f "/etc/letsencrypt/live/$1/fullchain.pem" ]
}

obtain_cert() {
    local first_domain="$1"
    shift
    echo "[certbot] Obtaining certificate for $first_domain ..."
    certbot certonly --webroot -w "$WEBROOT" \
        --non-interactive --agree-tos --no-eff-email \
        --email "$EMAIL" \
        "$@"
}

# ── Bootstrap: get initial certs if missing ──────────────────────────────────
if needs_cert "cmh.sh" || needs_cert "colinhayes.dev"; then
    echo "[entrypoint] Starting bootstrap nginx for ACME challenge..."
    nginx -c /etc/nginx/nginx-bootstrap.conf

    if needs_cert "cmh.sh"; then
        obtain_cert "cmh.sh" \
            -d cmh.sh -d ots.cmh.sh -d blog.cmh.sh -d blog4.cmh.sh
    fi

    if needs_cert "colinhayes.dev"; then
        obtain_cert "colinhayes.dev" \
            -d colinhayes.dev -d blog.colinhayes.dev \
            -d about.colinhayes.dev -d links.colinhayes.dev
    fi

    echo "[entrypoint] Stopping bootstrap nginx..."
    nginx -s stop
    # Give nginx a moment to fully stop before the main process starts
    sleep 2
fi

# ── Start nginx with full HTTPS config ───────────────────────────────────────
echo "[entrypoint] Starting nginx..."
nginx -g "daemon off;" &
NGINX_PID=$!

# ── Renewal loop (every 12 hours) ────────────────────────────────────────────
while true; do
    sleep 12h &
    wait $!
    echo "[certbot] Running renewal check..."
    certbot renew --webroot -w "$WEBROOT" --quiet \
        --deploy-hook "nginx -s reload"
done
