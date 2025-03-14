#!/bin/bash
#broken for some reason...
#tag=$(sudo docker images | grep -w vacuum-lb | head -1 | awk '{print $2}')
tagname="vacuumflask"
if [ -z "$1" ]; then
    tag=$(sudo docker images | grep -w ${tagname} | head -1 | awk '{print $2}')
else
    tag=$1
fi
echo "Version: $tag"
docker tag  vacuumflask:${tag} 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuumflask:${tag}
docker push 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuumflask:${tag}


#631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuumflask          202501s