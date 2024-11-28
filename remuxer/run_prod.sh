#!/bin/bash
if [ $# -eq 1 ]; then
  docker run --env-file /media/vacuum-data/.env \
    -e AWS_REGION=US-EAST-1 \
    --network="host" \
    -td $1
else
  echo "image id"
fi
