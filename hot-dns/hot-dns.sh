#!/bin/bash

aws s3 cp s3://internal.cmh.sh/config/hot-dns.txt working/hot-dns.txt

aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=*.internal.cmh.sh" "Name=instance-state-name,Values=running" \
    --query 'Reservations[].Instances[].[LaunchTime,PublicIpAddress,PrivateIpAddress,Tags[?Key==`Name`].Value | [0]]' \
    --output text --region us-east-1 > working/vacuumhosts.txt
rm working/dns.txt
while read -r Name Zone; do
    echo "Getting records for $Name @ $Zone"
    if [ -z "$Zone" ]; then
        echo "No zone found for $Name"
        continue
    fi
    data=$(aws route53 list-resource-record-sets \
        --hosted-zone-id "$Zone" \
        --query "ResourceRecordSets[?ends_with(Name, '$Name')].[ResourceRecords[].Value | [0], Name]" \
        --output text | sed 's/\.$//' | sed "s/$/ $Zone/")
    if [ -z "$data" ]; then
        echo "No records found for $Name"
        continue
    fi
    echo "$data" >> working/dns.txt 
done < working/hot-dns.txt
# Get all records and filter for internal.cmh.sh entries



public_ips=$(awk '{print $2}' working/vacuumhosts.txt ) #
    # Create the JSON array of IP values
    ip_json=$(echo "$public_ips" | awk '{
        if (NR == 1) {
            printf "[{\"Value\": \"%s\"}", $1
        } else {
            printf ",{\"Value\": \"%s\"}", $1
        }
    } END { print "]" }')
    echo "IP JSON: $ip_json"

while read -r PublicIpAddress dnsname zoneid; do
    ipfound=$(echo "$public_ips" | grep "$PublicIpAddress")
    if [ -z "$ipfound" ]; then
    
        echo "Updating $dnsname to $PublicIpAddress"
        result=$(aws route53 change-resource-record-sets \
        --hosted-zone-id ${zoneid} \
        --change-batch '{
            "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                "Name": "'"$dnsname"'",
                "Type": "A",
                "TTL": 300,
                "ResourceRecords": '"$ip_json"'
                }
            }
            ]
        }')
        echo "Result of update: $result"
    else
        echo "No update needed for $dnsname"
    fi
done < working/dns.txt
