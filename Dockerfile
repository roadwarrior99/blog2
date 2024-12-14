FROM public.ecr.aws/docker/library/python:3.12

WORKDIR /tmp
# Add  application
ADD app.py /tmp/app.py
ADD objects.py /tmp/objects.py
ADD hash.py /tmp/hash.py
ADD s3_management.py /tmp/s3_management.py
ADD image_processing.py /tmp/image_processing.py
ADD efs-utils.deb /tmp/efs-utils.deb

COPY templates /tmp/templates
COPY static /tmp/static

#FROM ubuntu:latest
RUN apt-get update -qq && apt-get install ffmpeg -y
RUN apt-get update -qq && apt-get install git binutils rustc cargo pkg-config libssl-dev gettext -y
RUN apt-get install -y nfs-common
RUN apt-get -y install /tmp/efs-utils.deb

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

#Make a temp dir for large uploads
RUN mkdir /tmp/downloads

EXPOSE 8080

# Run it
CMD [ "waitress-serve", "app:app" ]
