#!/bin/bash
version=$(date '+%Y%m%d_%H%M')
docker tag vacuumflask_worker:latest 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuumflask_worker:$version
docker push 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuumflask_worker:$version