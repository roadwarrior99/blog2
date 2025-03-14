#!/bin/bash
#broken for some reason...
images=$(docker images)
tag=$(echo $images | grep -w vacuum-lb | head -1 | awk '{print $2}')
echo "Version: ${tag}"
docker tag vacuum-lb:${tag} 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuum_lb:${tag}
docker push 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuum_lb:${tag}


