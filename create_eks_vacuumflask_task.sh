#!/bin/bash
 aws ecs register-task-definition --cli-input-json file://vacuumflask_eks_task.json --profile vacuum --region us-east-1


#https://aws.amazon.com/blogs/containers/developers-guide-to-using-amazon-efs-with-amazon-ecs-and-aws-fargate-part-3/