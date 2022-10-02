
FROM hansroh/ubuntu:aws

ENV PYTHONUNBUFFERED=0

COPY requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt && rm -f /requirements.txt

COPY tests/requirements.txt /requirements.txt
COPY tests/install.sh /install.sh
RUN /install.sh && rm -f /requirements.txt /install.sh

USER ubuntu
WORKDIR /home/ubuntu/app
EXPOSE 5000
