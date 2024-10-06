#!/bin/bash

docker build --tag vacuumflask .
imageid=$(docker image ls | grep -w "vacuumflask" | awk '{print $3}')
echo "new vacuumflask imageid: $imageid"
