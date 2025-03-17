#!/bin/bash
# This script updates the AWS EC2 launch template with a new user data script
TEMPLATE_ID="lt-0c516242b6cd994ca"

# Read and base64 encode the user data file
USER_DATA=$(base64 -i user-data-setup.sh)

# Get the latest version's configuration
aws ec2 describe-launch-template-versions \
    --launch-template-id $TEMPLATE_ID \
    --versions '$Latest' \
    --query 'LaunchTemplateVersions[0].LaunchTemplateData' \
    --output json \
    --profile vacuum \
    | tr -d '\n' > latest_config.tmp

echo "Updating launch template $TEMPLATE_ID"
# Update the UserData in the configuration
jq --arg ud "$USER_DATA" '. + {"UserData": $ud}' latest_config.tmp > updated_config.json

# Create new version with updated configuration
NEW_VERSION=$(aws ec2 create-launch-template-version \
    --launch-template-id $TEMPLATE_ID \
    --launch-template-data=file://updated_config.json \
    --query 'LaunchTemplateVersion.VersionNumber' \
    --output text \
    --profile vacuum)

if [ $? -ne 0 ]; then
    echo "Failed to create new launch template version"
    exit 1
fi

echo "Created new launch template version: $NEW_VERSION"

# Set the new version as default
aws ec2 modify-launch-template \
    --launch-template-id $TEMPLATE_ID \
    --default-version $NEW_VERSION \
    --profile vacuum


if [ $? -ne 0 ]; then
    echo "Failed to set new version as default"
    exit 1
else
    rm latest_config.tmp updated_config.json
fi
aws s3 cp user-data-setup.sh s3://internal.cmh.sh/config/user-data-setup.sh --profile vacuum
ssh project -t "sudo aws s3 cp s3://internal.cmh.sh/config/user-data-setup.sh /media/vacuum-data/user-data-setup.sh && sudo chmod +x /media/vacuum-data/user-data-setup.sh"
echo "Successfully set version $NEW_VERSION as default"

updated=$(date)
echo "Updated launch template $TEMPLATE_ID to version $NEW_VERSION on $updated"