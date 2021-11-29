FROM hansroh/ubuntu:aws
ARG DEBIAN_FRONTEND=noninteractive

LABEL title="Skitai Package Group Development"
LABEL author="hansroh"
LABEL version="1.0"

RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ bionic-pgdg main" | tee /etc/apt/sources.list.d/pgdg.list
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
RUN apt update && apt install -y postgresql-12
RUN apt install -y libjpeg-dev libssl-dev

COPY requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt
RUN rm /requirements.txt

ENV MYDB="skitai:12345678@localhost/skitai"

EXPOSE 5000
CMD [ "/bin/bash" ]
