#!/bin/bash
#temp copy shared library from parent dir
cp ../s3_management.py s3_management.py
docker build --tag vacuumflask_worker .
imageid=$(docker image ls | grep -w "vacuumflask_worker" | awk '{print $3}')
echo "new vacuumflask_worker imageid: $imageid"
#clean temp shared library so we don't end up with more than one.
rm s3_management.py
