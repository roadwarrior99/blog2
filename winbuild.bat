@echo off
set tagname=%1
set version=%2
set logfile=winbuild_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log

echo [%date% %time%] Starting build for %tagname%:%version% >> %logfile%

if "%tagname%"=="" (
    echo Usage: winbuild.bat tagname version
    echo [%date% %time%] ERROR: Missing tagname parameter >> %logfile%
    exit /b 1
)

if "%version%"=="" (
    echo Usage: winbuild.bat tagname version
    echo [%date% %time%] ERROR: Missing version parameter >> %logfile%
    exit /b 1
)

echo [%date% %time%] Starting docker build >> %logfile%
docker build --tag %tagname%:%version% --tag %tagname%:latest . >> %logfile% 2>&1
if %errorlevel% neq 0 (
    echo Docker build failed
    echo [%date% %time%] ERROR: Docker build failed with code %errorlevel% >> %logfile%
    exit /b %errorlevel%
)
echo [%date% %time%] Docker build successful >> %logfile%

echo [%date% %time%] Starting AWS ECR login >> %logfile%
aws ecr get-login-password --region us-east-1 --profile vacuum | docker login --username AWS --password-stdin 631538352062.dkr.ecr.us-east-1.amazonaws.com >> %logfile% 2>&1
if %errorlevel% neq 0 (
    echo AWS ECR login failed
    echo [%date% %time%] ERROR: AWS ECR login failed with code %errorlevel% >> %logfile%
    exit /b %errorlevel%
)
echo [%date% %time%] AWS ECR login successful >> %logfile%

echo [%date% %time%] Tagging image >> %logfile%
docker tag %tagname%:%version% 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/%tagname%:%version% >> %logfile% 2>&1

echo [%date% %time%] Pushing image to ECR >> %logfile%
docker push 631538352062.dkr.ecr.us-east-1.amazonaws.com/cmh.sh/%tagname%:%version% >> %logfile% 2>&1

echo [%date% %time%] Build process completed >> %logfile%