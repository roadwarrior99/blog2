FROM public.ecr.aws/amazonlinux/amazonlinux:2023
WORKDIR /tmp
RUN mkdir /tmp/working
ADD hot-dns.sh /tmp/hot-dns.sh
CMD [ "sh", "/tmp/hot-dns.sh" ]