#!/bin/bash
tagname="vacuumflask"
version=$(date +"%Y%m%d%H%M%S")
docker build --tag "${tagname}:${version}" --tag ${tagname}:latest .
imageid=$(docker image ls | grep -w "vacuumflask" | awk '{print $3}')
echo "new vacuumflask imageid: $imageid"
