#!/bin/bash
imageid=$(docker images | grep "vacuumflask" | awk '{print $3}')
echo "running image $imageid"
docker run --env-file /media/vacuum-data/.env \
	--volume /media/vacuum-data/data:/tmp/data \
	--volume /media/vacuum-data/templates:/tmp/templates \
	--volume /media/vacuum-data/static:/tmp/static \
	--network="host" \
	-e AWS_REGION=US-EAST-1 \
	-td "$imageid"