#!/bin/bash
#Grab a list of stopped docker containers
docker ps -a | grep -w Exited | grep -E "months|weeks" | awk '{print $1}' > old_containers.txt
while IFS= read -r instance
do
        docker container rm $instance
done < old_containers.txt
if [ -f old_containers.txt ]; then
        rm old_containers.txt
fi

#Grab a list of bad docker images
docker images | grep -w "<none>" | awk '{print $3}' > bad_images.txt
#loop through and delete them.
while IFS= read -r image
do
        docker image rm $image
done < bad_images.txt
#remove bad_images file
if [ -f bad_images.txt ]; then
        rm bad_images.txt
fi