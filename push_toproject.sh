#!/bin/bash
destination="beanstalk/"
zipPrefix="vacuumflask-"
zipPostfix=$(date '+%Y%m%d')
zipFileName="$zipPrefix$zipPostfix.zip"
mkdir "$destination"
cp -a templates/. "$destination/templates"
cp -a static/. "$destination/static"
cp app.py "$destination"
cp Dockerfile "$destination"
cp hash.py "$destination"
cp objects.py "$destination"
cp s3_management.py "$destination"
cp image_processing.py "$destination"
cp requirements.txt "$destination"
cd "$destination"
zip -r "../$zipFileName" "."
cd ../
rm -r "$destination"
scp "$zipFileName" project:blog2
ssh project "cd /media/vacuum-data;sudo mv /home/ubuntu/blog2/$zipFileName /media/vacuum-data/$zipFileName;sudo bash deploy.sh $zipFileName"
ssh mail "cd /media/vacuum-data; sudo bash deploy.sh"
