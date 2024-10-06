#!/bin/bash
#Check if we have a parameter
if [ $# -eq 1 ]; then
	#check if the parameter is a file that exists
	if [ -f "$1" ]; then
	unzip -o "$1"
	rm "$1"
	fi
fi
oldimage=$(docker images | grep -w vacuumflask | awk '{print $3}')
newimageid=$(sh build.sh | awk '{print $4}')
runninginstance=$(docker ps | grep -w "$oldimage" | awk '{print $1}')
#echo "running instances: $runningistance"
while IFS= read -r instance; do
	docker kill "$instance"	
done <<< "$runninginstance"
sh run.sh
sh run2.sh
nowrunninginstance=$(docker ps | grep -w "$newimageid" | awk '{print $1}')
docker ps
echo "new running instance id is: $nowrunninginstance"
