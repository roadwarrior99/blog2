FROM public.ecr.aws/docker/library/python:3.12

WORKDIR /tmp
# Add  application
ADD s3_management.py /tmp/s3_management.py
ADD worker.py /tmp/worker.py


#FROM ubuntu:latest
RUN apt-get update -qq && apt-get install ffmpeg -y

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt
#Add a temp dir for downloads from S3
#We may map over this in AWS to EFS storage for greater flexability in file size
RUN mkdir /tmp/downloads
# Run it
CMD [ "python3", "/tmp/worker.py" ]
