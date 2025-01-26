#!/bin/bash
if [ -z "$1" ]; then
    echo "Usage: $0 <file> to unpack"
    exit 1
fi
unzip -o $1
rm $1
