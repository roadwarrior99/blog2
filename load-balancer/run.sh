#!/bin/bash
tagname="vacuum-lb"
docker pull 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh:$tagname
img=$( docker images | grep  $tagname | head -1 | awk '{print $3}')
echo "running image $img"
docker run \
--volume /media/vacuum-data/vacuum-lb/logs:/var/log/nginx \
--volume /media/vacuum-data/vacuum-lb/ssl:/tmp/ssl \
--volume /media/vacuum-data/vacuum-lb/nginx.conf:/etc/nginx/nginx.conf \
--volume /media/vacuum-data/vacuum-lb/dns.conf:/etc/resolv.conf \
-e AWS_REGION=US-EAST-1 \
-p 443:443 -p 8099:80 -td "$img"
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