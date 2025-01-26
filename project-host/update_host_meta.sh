#!/bin/bash
if [ #$ -eq 0 ]; then
    echo "hostname ip"
    echo "Usage: $0 dns name to connect to and update hosts/hostname"
    echo "This will trigger a reboot, so maybe run it last."
    exit 1
fi
localname=$(hostname);
commands_to_run="hostname $1; echo $1 > /etc/hostname; echo 127.0.0.1 $1 > /etc/hosts; echo $1 >> /etc/hosts; reboot;"
if [ $1 -eq $localname ]; then
    echo "Local change";
    eval $commands_to_run
else
    echo "Remote change;"
    ssh $2 $commands_to_run  
fi
