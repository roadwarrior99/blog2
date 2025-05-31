#!/bin/bash
. ./create_eks_vacuumflask_env.sh
aws ecs create-service  --cluster vacuum-flask \
  --service-name vacuumflask  \
  --task-definition vacuumflask_workers \
  --desired-count 1  --launch-type FARGATE  \
  --profile vacuum --region us-east-1 \
  --network-configuration "awsvpcConfiguration={subnets=[${PRIVATE_SUBNET1},${PRIVATE_SUBNET2}],securityGroups=[${VF_SG_ID}],assignPublicIp=DISABLED}" \
  #--load-balancers targetGroupArn=${VF_TARGET_GROUP_ARN},containerName=vacuumflask,containerPort=8080,loadBalancerName=vacuumflask-ecs-nlb


#aws ecs create-service  --cluster vacuumflask_workers  --service-name vacuumflask-web  --task-definition vacuumflask_workers  --desired-count 2  --launch-type FARGATE  --load-balancers targetGroupArn=${VF_TARGET_GROUP_ARN},containerName=application,containerPort=8080  --network-configuration "awsvpcConfiguration={subnets=[${PRIVATE_SUBNET1},${PRIVATE_SUBNET2}],securityGroups=[${VF_SG_ID}],assignPublicIp=DISABLED}" --profile vacuum --region us-east-1

#FARGATE
#service vacuumflask failed to launch a task with (error ECS was unable to assume the role 'arn:aws:iam::631538352062:role/ecs_vacuumflask_taskrole' that was provided for this task. Please verify that the role being passed has the proper trust relationship and permissions and that your IAM user has permissions to pass this role.).
#https://repost.aws/knowledge-center/ecs-unable-to-assume-role
#was fix ^