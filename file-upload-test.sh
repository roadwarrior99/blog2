#!/bin/bash
#Grab login and password
if [ $# -eq 1 ]
then
  echo "enter password dummy:"
  stty -echo
  read -r password
  stty echo

  curl -X POST http://localhost:5000/login \
       -H "Content-Type: application/x-www-form-urlencoded" \
       -d "username=colin" \
       -d "password=$password" \
       -c cookie.txt
  curl -v -F "file=@$1" localhost:5000/upload -b cookie.txt
else
  echo "<please pass in a file to upload.>"
fi