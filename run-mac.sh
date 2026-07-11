#!/bin/bash
if [ $# -eq 1 ]; then
	imageid=$1
else
	imageid=$(docker images | grep "vacuumflask" | awk '{print $1}' | sort -r)
fi
echo "running image $imageid"
docker run --env-file .env \
	--volume data:/tmp/data \
	--volume templates:/tmp/templates \
	--volume static:/tmp/static \
	--network="host" \
	--user 1000 \
	-e AWS_REGION=US-EAST-1 \
	-td "$imageid" \
	-p 8080:8080
