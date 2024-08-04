#!/bin/bash

docker build --tag vacuumflask .
imageid=$(docker image ls | grep -w "vacuumflask" | awk '{print $3}')
docker run  --env-file "/home/colin/python/blog2/vacuumflask/.env" \
--volume /home/colin/python/blog2/vacuumflask/data:/tmp/data \
-p 8080:8080 \
 "$imageid"