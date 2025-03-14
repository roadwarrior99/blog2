#!/bin/bash
# Secret ARN
SECRET_ARN="arn:aws:secretsmanager:us-east-1:631538352062:secret:vacuumflask-YmcOKn"

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
sudo yum -y install vim screen
sudo yum -y install jq
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
sudo docker pull 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuum_lb:latest
sudo docker pull 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/apachesites:latest
sudo sh /media/vacuum-data/run.sh
bash /media/vacuum-data/update_internal_dns_auto.sh
bash /media/vacuum-data/projectbox-run.sh

#Kubernetes related

if [ -z K3S_URL ]; then
  export K3S_URL=$(cat /media/vacuum-data/k3s/k3s_url)
fi
if [ -z K3S_TOKEN ]; then
  export K3S_TOKEN=$(cat /media/vacuum-data/k3s/k3s_token)
fi
if [ -z postgres_server ]; then
  export postgres_server=$(cat /media/vacuum-data/k3s/postgres_server)
fi
if [ -z postgres_port ]; then
  export postgres_port=$(cat /media/vacuum-data/k3s/postgres_port)
fi
# Get the secret value and store it in a variable
secret_string=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_ARN" \
    --query 'SecretString' \
    --output text)
# Parse the JSON and extract the values using jq
# Note: You'll need to install jq if not already installed: sudo yum install -y jq
export K3S_POSTGRES_USER=$(echo $secret_string | jq -r '.K3S_POSTGRES_USER')
export K3S_POSTGRES_PASSWORD=$(echo $secret_string | jq -r '.K3S_POSTGRES_PASSWORD')
export POSTGRESS_SERVER=$(echo $secret_string | jq -r '.POSTGRES_SERVER')

if [ -z postgres_conn_k3s ]; then
  con="mysql://$K3S_POSTGRES_USER:$K3S_POSTGRES_PASSWORD@tcp($POSTGRESS_SERVER:3306)/k3s"
  export postgres_conn_k3s=${con}
fi
curl -sfL https://get.k3s.io | sh -s - server \
  --token=${K3S_TOKEN} \
  --datastore-endpoint=${postgres_conn_k3s}

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
sudo yum -y install kubectl


#ECS related
if [ -d /etc/ecs ]; then
  echo "ECS_CLUSTER=vacuumflask_workers" > /etc/ecs/ecs.config
  echo "ECS_BACKEND_HOST=" >> /etc/ecs/ecs.config
  #TODO: set hostname; set name in /etc/hosts
  #TODO: register with ALB.
fi

