#!/bin/bash
# Clean up any previous build
rm -rf package lambda.zip

# Create package directory
mkdir -p package

# Install dependencies
pip install -r requirements.txt -t package/

# Copy the Lambda function
cp lambda_function.py package/lambda_function.py

# Create the zip file
cd package
zip -r ../lambda.zip .
cd ..

# Update the Lambda function
aws lambda update-function-code --function-name Vacuum-baas --zip-file fileb://lambda.zip > create-status.json

date

