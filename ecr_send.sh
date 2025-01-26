#!/bin/bash
#broken for some reason...
tag=$(docker images | grep -w vacuum-lb | head -1 | awk '{print $2}')
echo "Version: ${tag}"
docker tag vacuumflask:${tag} 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh:vacuumflask
docker push 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh:vacuum-lb


