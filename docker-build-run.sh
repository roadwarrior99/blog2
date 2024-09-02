#!/bin/bash

docker build --tag vacuumflask .
imageid=$(docker image ls | grep -w "vacuumflask" | awk '{print $3}')
#
aws ecr get-login-password --region us-east-1 --profile vacuum | docker login --username AWS --password-stdin 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh
docker tag "$imageid" 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh:vacuumflask
docker push 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh:vacuumflask
#docker run  --env-file "/home/colin/python/blog2/vacuumflask/.env" \
#--volume /home/colin/python/blog2/vacuumflask/data:/tmp/data \
#-p 8080:8080 \
"$imageid"
