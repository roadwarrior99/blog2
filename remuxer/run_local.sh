#!/bin/bash
if [ $# -eq 1 ]; then
  docker run --env-file /home/colin/PycharmProjects/blog2/.env \
    --volume /home/colin/.aws:/root/.aws \
    $1
else
  echo "image id"
fi
