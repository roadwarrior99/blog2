#!/bin/bash
tagname="vacuum-lb"
version=$(date +"%Y%m%d%H%M%S")
docker build --tag "${tagname}:${version}" .
success=$(docker images | grep -w $version)
if [ -z "$success" ]; then
    echo "build failed"
    exit 1
fi
imageid=$(docker image ls | grep -w "$tagname" | awk '{print $3}')
#echo "new imageid: $imageid"
lastimage=$(head -1 <<< $imageid)
old_containers=$(docker ps -a | grep -w "$tagname"| grep -w Exited | grep -E "months|weeks|days|hours" | awk '{print $1}')
while IFS= read -r instance
do
        docker container rm "$instance"
done <<< "$old_containers"
echo "cleaning up old images"
while IFS= read -r image; do
    if [ "$image" != "$lastimage" ]; then
        echo "removing image: $image"
        docker rmi $image
    fi
done <<< "$imageid"
echo "last imageid: $lastimage"
created=$(docker images | grep -w $lastimage | awk '{print $4}')
echo "created: $created"