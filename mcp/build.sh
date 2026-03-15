#!/bin/bash
tagname="vacuum-mcp"
version=$(date +"%Y%m%d%H%M%S")
docker build --tag "${tagname}:${version}" --tag ${tagname}:latest .
imageid=$(docker image ls | grep -w "$tagname" | awk '{print $3}')
echo "new $tagname imageid: $imageid"
