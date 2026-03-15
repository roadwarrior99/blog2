#!/bin/bash
certbot renew --webroot -w /var/www/certbot --quiet && nginx -s reload