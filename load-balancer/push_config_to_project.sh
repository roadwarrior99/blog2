#!/bin/bash
destination="vacuum-lb-push"
zipPrefix="vacuum-lb-"
zipFileName="$zipPrefix$(date +%Y%m%d).zip"
mkdir $destination
while IFS= read -r file; do
    cp $file $destination/$file
done < ship_list.txt
cd $destination
zip -r $zipFileName *
mv $zipFileName ../.
cd ../
rm -rf $destination
scp $zipFileName project:blog2/$zipFileName
ssh project "cd /media/vacuum-data/vacuum-lb; sudo mv /home/ubuntu/blog2/$zipFileName /media/vacuum-data/vacuum-lb/$zipFileName; sudo bash unpack.sh $zipFileName"
rm $zipFileName