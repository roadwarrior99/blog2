#!/bin/bash
tagname="vacuum-lb"
docker pull 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh:$tagname
img=$(docker images | grep $tagname | head -1 | awk '{print $3}')
echo "running image $img"
docker run \
  --volume /media/vacuum-data/vacuum-lb/logs:/var/log/nginx \
  --volume /media/vacuum-data/vacuum-lb/letsencrypt:/etc/letsencrypt \
  --volume /media/vacuum-data/vacuum-lb/certbot-www:/var/www/certbot \
  --volume /media/vacuum-data/vacuum-lb/nginx.conf:/etc/nginx/nginx.conf \
  --volume /media/vacuum-data/vacuum-lb/dns.conf:/etc/resolv.conf \
  -e CERTBOT_EMAIL=colin@cmh.sh \
  -e AWS_REGION=US-EAST-1 \
  -p 80:80 -p 443:443 \
  -td "$img"
