@echo off
set tagname=%1
set version=%2

if "%tagname%"=="" (
    echo Usage: winbuild.bat tagname version
    exit /b 1
)

if "%version%"=="" (
    echo Usage: winbuild.bat tagname version
    exit /b 1
)

docker build --tag %tagname%:%version% --tag %tagname%:latest .
if %errorlevel% neq 0 (
    echo Docker build failed
    exit /b %errorlevel%
)

aws ecr get-login-password --region us-east-1 --profile vacuum | docker login --username AWS --password-stdin 631538352062.dkr.ecr.us-east-1.amazonaws.com
if %errorlevel% neq 0 (
    echo AWS ECR login failed
    exit /b %errorlevel%
)

docker tag %tagname%:%version% 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/%tagname%:%version%
docker push 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/%tagname%:%version%