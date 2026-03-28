FROM public.ecr.aws/nginx/nginx
COPY nginx.conf /etc/nginx/nginx.conf
RUN mkdir /tmp/ssl
RUN apt-get update -qq && apt-get install -y certbot python3-certbot-nginx cron openssl && rm -rf /var/lib/apt/lists/*

# Renewal script
COPY certbot-renew.sh /etc/cron.daily/certbot-renew
RUN chmod +x /etc/cron.daily/certbot-renew

# Run renewal at 03:00 and 15:00 daily
RUN echo "0 3,15 * * * root /etc/cron.daily/certbot-renew >> /var/log/nginx/certbot-renew.log 2>&1" > /etc/cron.d/certbot-renew \
    && chmod 0644 /etc/cron.d/certbot-renew

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]

