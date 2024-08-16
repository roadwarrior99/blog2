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
cp requirements.txt "$destination"
cd "$destination"
zip -r "../$zipFileName" "."
cd ../
rm -r "$destination"
scp "$zipFileName" project:blog2
scp docker-build-run.sh project:blog2
ssh project