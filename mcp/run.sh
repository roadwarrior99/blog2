#!/bin/bash
docker run -d \
    --name vacuum-mcp \
    -p 8001:8001 \
    -v /media/vacuum-data/data:/data:ro \
    --env-file .env \
    vacuum-mcp
