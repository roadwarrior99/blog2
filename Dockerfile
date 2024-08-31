FROM public.ecr.aws/docker/library/python:3.12

WORKDIR /tmp
# Add  application
ADD app.py /tmp/app.py
ADD objects.py /tmp/objects.py
ADD hash.py /tmp/hash.py
ADD s3_management.py /tmp/s3_management.py

COPY templates /tmp/templates
COPY static /tmp/static


COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

EXPOSE 8080

# Run it
CMD [ "waitress-serve", "app:app" ]
