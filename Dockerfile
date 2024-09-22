FROM public.ecr.aws/docker/library/python:3.12

WORKDIR /tmp
# Add  application
ADD app.py /tmp/app.py
ADD objects.py /tmp/objects.py
ADD hash.py /tmp/hash.py
ADD s3_management.py /tmp/s3_management.py
ADD image_processing.py /tmp/image_processing.py

COPY templates /tmp/templates
COPY static /tmp/static

FROM ubuntu:latest
RUN apt-get update -qq && apt-get install ffmpeg -y

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

EXPOSE 8080

# Run it
CMD [ "waitress-serve", "app:app" ]
