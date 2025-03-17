#!/bin/bash
version=$(date +%Y%m%d%H%M)
echo "Building hot-dns:${version}"
docker build --tag hot-dns:latest --tag hot-dns:${version} .

