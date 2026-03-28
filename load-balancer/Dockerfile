FROM public.ecr.aws/nginx/nginx

RUN apt-get update && \
    apt-get install -y certbot && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/www/certbot /etc/letsencrypt /tmp/ssl

COPY nginx-bootstrap.conf /etc/nginx/nginx-bootstrap.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
