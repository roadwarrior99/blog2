#!/bin/zsh
docker tag redis:latest 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh:redis
docker push 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh:redis
