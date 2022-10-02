ARG DOCKER_TAG=latest
FROM docker:${DOCKER_TAG}

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL title="AWS Cli and Docker Compose"
LABEL author="hansroh"
LABEL version="1.0"

ENV LC_ALL=C.UTF-8

RUN wget https://github.com/docker/compose-cli/releases/download/v1.0.29/docker-linux-amd64 && \
        mv docker-linux-amd64 docker && chmod +x docker && \
        mv /usr/local/bin/docker /usr/local/bin/com.docker.cli && \
        mv docker /usr/local/bin/docker;

RUN apk add --update --no-cache python3 curl jq zip
RUN python3 -m ensurepip

RUN apk add --no-cache --virtual .build-deps gcc musl-dev python3-dev; \
    pip3 install awscli python-telegram-bot; \
    apk del .build-deps;

COPY include/telegram.py /usr/bin/telegram
RUN chmod +x /usr/bin/telegram
COPY include/wait-for-it.sh /usr/bin/wait-for-it.sh
RUN chmod +x /usr/bin/wait-for-it.sh