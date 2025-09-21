#!/bin/bash
destination="beanstalk/"
zipPrefix="vacuumflask-"
zipPostfix=$(date '+%Y%m%d')
zipFileName="$zipPrefix$zipPostfix.zip"
mkdir "$destination"
cp -a templates/. "$destination/templates"
cp -a static/. "$destination/static"
cp app.py "$destination"
cp efs-utils.deb "$destination"
cp Dockerfile "$destination"
cp hash.py "$destination"
cp objects.py "$destination"
cp efs-utils.deb "$destination"
cp s3_management.py "$destination"
cp image_processing.py "$destination"
cp requirements.txt "$destination"
cd "$destination"
zip -r "../$zipFileName" "."
cd ../
rm -r "$destination"
scp "$zipFileName" fck-nat:.
ssh fck-nat "cd /media/vacuum-data;sudo mv /home/ec2-user/$zipFileName /media/vacuum-data/$zipFileName;sudo unzip -o $zipFileName;sudo rm $zipFileName;"

