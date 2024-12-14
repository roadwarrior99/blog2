#!/bin/bash
git clone https://github.com/aws/efs-utils
cd efs-utils
sh build-deb.sh
apt-get -y install /tmp/efs-utils/build/amazon-efs-utils*deb
