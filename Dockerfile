FROM hansroh/ubuntu:aws
ARG DEBIAN_FRONTEND=noninteractive

LABEL title="Skitai Package Group Development"
LABEL author="hansroh"
LABEL version="1.0"

RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ bionic-pgdg main" | tee /etc/apt/sources.list.d/pgdg.list
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
RUN apt update && apt install -y postgresql-12
RUN apt install -y libjpeg-dev libssl-dev

ENV MYDB="skitai:12345678@localhost/skitai"
RUN pip3 install -U django sqlphile psycopg2-binary
COPY benchmark benchmark

RUN pg_ctlcluster 12 main start; \
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

# see tools/docker/README.md