FROM hansroh/aws

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL title="Skitai Package Group Development"
LABEL author="hansroh"
LABEL version="1.0"

RUN apt update
RUN apt install -y postgresql postgresql-contrib

RUN pip3 install -U pip
RUN pip3 install -U django sqlphile psycopg2-binary
COPY benchmark benchmark

ENV MYDB="skitai:12345678@localhost/skitai"
RUN service postgresql start; \
    su - postgres -c "psql -c \"drop database if exists skitai;\""; \
    su - postgres -c "psql -c \"create database skitai;\""; \
    su - postgres -c "psql -c \"create user skitai with encrypted password '12345678';\""; \
    su - postgres -c "psql -c \"grant all privileges on database skitai to skitai;\""; \
    cd benchmark; \
    python3 bench/manage.py migrate; \
    python3 bench/init_db.py; \
    rm -rf benchmark;

COPY tools/docker/requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt && rm -f /requirements.txt

WORKDIR /home/ubuntu/libs/skitai
EXPOSE 5000
CMD [ "/bin/bash" ]
