#!/bin/bash
repo="631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuum_lb"
tagname=$(aws ecr describe-images --repository-name cmh.sh/vacuum_lb --region us-east-1 \
    --query 'sort_by(imageDetails, &imagePushedAt)[-1].imageTags[0]' --output text)
echo "pulling latest tag: $tagname"
docker pull "$repo:$tagname"
img="$repo:$tagname"
echo "running image $img"
docker run \
--volume /media/vacuum-data/vacuum-lb/logs:/var/log/nginx \
--volume /media/vacuum-data/vacuum-lb/ssl:/tmp/ssl \
--volume /media/vacuum-data/vacuum-lb/nginx.conf:/etc/nginx/nginx.conf \
--volume /media/vacuum-data/vacuum-lb/dns.conf:/etc/resolv.conf \
--volume /media/vacuum-data/vacuum-lb/letsencrypt:/etc/letsencrypt \
--restart unless-stopped \
-e AWS_REGION=us-east-1 \
-p 443:443 -p 80:80 -td "$img"
#echo "waiting for container to start"
#sleep 5
#contid=$(docker ps -a | grep "$img" | awk '{print $1}')
#echo "container id is $contid"S
#status=$(docker ps -a | grep "$contid" | awk '{print $7}')
#echo "container status is $status"
#if [ "$status" != "Up" ]; then
#    echo "container failed to start"
#    docker logs "$contid"
#    echo "removing container"
#    docker rm "$contid"
#fi