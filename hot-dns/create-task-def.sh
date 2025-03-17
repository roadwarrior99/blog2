#!/bin/bash
aws ecs register-task-definition --cli-input-json file://hot-dns-task-def.json

