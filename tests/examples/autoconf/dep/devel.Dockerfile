FROM hansroh/ubuntu:aws

ENV PYTHONUNBUFFERED=0
COPY requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt && rm -f /requirements.txt

WORKDIR /home/ubuntu/app
EXPOSE 5000
CMD ["./dep/devel.sh"]
