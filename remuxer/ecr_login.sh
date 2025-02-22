#!/bin/bash
aws ecr get-login-password --region us-east-1 --profile vacuum | sudo docker login --username AWS --password-stdin 631538352062.dkr.ecr.us-east-1.amazonaws.com
