#!/bin/bash
sudo yum update
sudo yum upgrade -y
#Install EFS utils
sudo yum install -y amazon-efs-utils
#sudo apt-get -y install git binutils rustc cargo pkg-config libssl-dev gettext
#git clone https://github.com/aws/efs-utils
#cd efs-utils
#./build-deb.sh
#sudo apt-get -y install ./build/amazon-efs-utils*deb
sudo yum -y install docker
sudo systemctl enable docker
sudo systemctl start docker
#sudo yum -y install boto3
if [ ! -d /media/vacuum-data ]; then
  sudo mkdir /media/vacuum-data
fi
echo "fs-05863c9e54e7cdfa4:/ /media/vacuum-data efs _netdev,noresvport,tls,iam 0 0" >> /etc/fstab
#sudo systemctl daemon-reload
sudo mount -a

#docker start redis
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 631538352062.dkr.ecr.us-east-1.amazonaws.com
sudo docker pull 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh:vacuumflask
sudo sh /media/vacuum-data/run.sh


