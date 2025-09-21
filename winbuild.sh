#!/bin/bash
# Build script for building on Win10VM2
tagname="vacuumflask"
version=$(date +"%Y%m%d%H%M%S")
ssh win10vm2 "f:; cd blog2; git pull; winbuild.bat $tagname $version"
#echo ""
#buildcmd="docker build --tag $tagname:$version --tag $tagname:latest"
#ssh win10vm2 "$buildcmd"
#images=$(ssh win10vm2 "docker image ls'")
#imageid=$(echo "$images" | grep -w "vacuumflask" | awk '{print $3}')
#echo "new vacuumflask imageid: $imageid"
#ssh win10vm2 "aws ecr get-login-password --region us-east-1 --profile vacuum | docker login --username AWS --password-stdin 631538352062.dkr.ecr.us-east-1.amazonaws.com"

#sendtoecr="docker tag vacuumflask:20250920631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuumflask:$version;
#docker push 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuumflask:$version"

#ssh win10vm2 "$sendtoecr"
#echo "pushed to ecr"
