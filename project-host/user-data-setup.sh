#!/bin/bash
# Secret ARN
SECRET_ARN="arn:aws:secretsmanager:us-east-1:631538352062:secret:vacuumflask-YmcOKn"
export CONFIG_FILE="/opt/aws/amazon-cloudwatch-agent/etc/cloud-watch-config.json"
export LOG_GROUP="vacuum-host"


sudo yum update
sudo yum upgrade -y
sudo yum -y install amazon-cloudwatch-agent
#configure cloudwatch

aws s3 cp s3://internal.cmh.sh/config/cloud-watch-config.json cloudwatch-config.json
# Stop the agent if it's running
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a stop

# Apply the configuration and start the agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:cloudwatch-config.json

# Enable the agent to start on boot
sudo systemctl enable amazon-cloudwatch-agent
sudo systemctl start amazon-cloudwatch-agent


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
sudo yum -y install git
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
#sudo docker pull 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/vacuum_lb:latest
#sudo docker pull 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/apachesites:latest
#sudo sh /media/vacuum-data/run.sh
#bash /media/vacuum-data/update_internal_dns_auto.sh
#bash /media/vacuum-data/projectbox-run.sh

source /media/vacuum-data/update_internal_dns_auto.sh

#Kubernetes related
sudo curl -sSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash

mkdir /tmp/working
chmod 777 /tmp/working


K3S_URL=$(cat /media/vacuum-data/k3s/k3s_url)
K3S_TOKEN=$(cat /media/vacuum-data/k3s/k3s_token)

# Get the secret value and store it in a variable
secret_string=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_ARN" \
    --query 'SecretString' \
    --output text)
# Parse the JSON and extract the values using jq
# Note: You'll need to install jq if not already installed: sudo yum install -y jq
K3S_POSTGRES_USER=$(echo $secret_string | jq -r '.K3S_POSTGRES_USER')
K3S_POSTGRES_PASSWORD=$(echo $secret_string | jq -r '.K3S_POSTGRES_PASSWORD')
POSTGRESS_SERVER=$(echo $secret_string | jq -r '.POSTGRES_SERVER')
con="postgres://$K3S_POSTGRES_USER:$K3S_POSTGRES_PASSWORD@$POSTGRESS_SERVER:5432/kubernetes"
postgres_conn_k3s=${con}
echo "postgres_conn_k3s is set to $postgres_conn_k3s"

# Download the RDS CA bundle
curl -O https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

# For k3s configuration, you'll want to move it to a permanent location
sudo mkdir -p /etc/kubernetes/pki/
sudo mv global-bundle.pem /etc/kubernetes/pki/rds-ca.pem

#ECS related
if [ -d /etc/ecs ]; then
  echo "ECS_CLUSTER=vacuumflask_workers" > /etc/ecs/ecs.config
  echo "ECS_BACKEND_HOST=" >> /etc/ecs/ecs.config
  #TODO: set hostname; set name in /etc/hosts
  #TODO: register with ALB.
fi

MAX_ATTEMPTS=60  # 5 minutes maximum wait time
ATTEMPT=0
API_URL="https://vacuumhost1.internal.cmh.sh:6443"

# Check if a k3s node is already online
response=$(curl -s -o /dev/null -w "%{http_code}" \
  --connect-timeout 5 \
  --max-time 10 \
  --insecure \
  "$API_URL")
if [ $? -eq 0 ] && [ "$response" -eq 401 ]; then
  curl -sfL https://get.k3s.io | sh -s - server \
    --token=${K3S_TOKEN} \
    --datastore-endpoint=${postgres_conn_k3s} \
    --log /var/log/k3s.log \
    --tls-san=${API_URL} 
else
  # Install k3s with PostgreSQL as the datastore
  #this is only if there isn't an existing k3s node
  curl -sfL https://get.k3s.io | sh -s - server \
    --write-kubeconfig-mode=644 \
    --datastore-endpoint=${postgres_conn_k3s} \
    --log /var/log/k3s.log \
    --datastore-cafile=/etc/kubernetes/pki/rds-ca.pem \
    --token=${K3S_TOKEN} \
  #  --tls-san=${K3S_URL} \
fi




echo "Waiting for k3s API server to start at $API_URL..."

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Perform curl with timeout and silent mode
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        --connect-timeout 5 \
        --max-time 10 \
        --insecure \
        "$API_URL")
    
    if [ $? -eq 0 ] && [ "$response" -eq 401 ]; then
        echo "K3s API server is ready!"
        break;
    else
        ATTEMPT=$((ATTEMPT + 1))
        remaining=$((MAX_ATTEMPTS - ATTEMPT))
        echo "Waiting... (got response code: $response, attempts remaining: $remaining)"
        sleep 5
    fi
done
if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "K3s API server did not start in time. Exiting."
    exit 1
fi

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
pwd=$(aws ecr get-login-password)
echo $pwd | sudo docker login --username AWS --password-stdin 631538352062.dkr.ecr.us-east-1.amazonaws.com
kubectl delete secret regcred --namespace=default
# Create a secret named 'regcred' in your cluster
kubectl create secret docker-registry regcred \
  --docker-server=631538352062.dkr.ecr.us-east-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password=${pwd} \
  --namespace=default

kubectl create secret tls colinhayes-tls \
  --cert=/media/vacuum-data/vacuum-lb/ssl/wild.colinhayes.dev.25.pem \
  --key=/media/vacuum-data/vacuum-lb/ssl/wild.colinhayes.dev.25.key \
  --namespace=default

kubectl create secret tls cmh-tls \
  --cert=/media/vacuum-data/vacuum-lb/ssl/wild.cmh.sh.crt \
  --key=/media/vacuum-data/vacuum-lb/ssl/wild.cmh.sh.key \
  --namespace=default


helm repo add traefik https://traefik.github.io/charts
helm repo update
helm install traefik traefik/traefik --namespace traefik --create-namespace
kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v2.10/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml

cd /media/vacuum-data/k3s
source /media/vacuum-data/k3s/setup-all.sh prod




