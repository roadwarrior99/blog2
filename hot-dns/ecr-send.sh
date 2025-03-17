#!/bin/bash
version=$(sudo docker images | grep hot-dns | awk '{print $2}' | head -n 1)
echo "Version: ${version}"
docker tag hot-dns:latest 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/hot-dns:latest
docker tag hot-dns:${version} 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/hot-dns:${version}
docker push 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/hot-dns:latest
docker push 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/hot-dns:${version}