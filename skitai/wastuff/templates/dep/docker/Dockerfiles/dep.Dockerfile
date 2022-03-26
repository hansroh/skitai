FROM tmaier/docker-compose:latest
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL title="AWS Cli and Docker Compose"
LABEL author="hansroh"
LABEL version="1.0"

ENV LC_ALL=C.UTF-8

RUN apk add --update --no-cache python3 curl jq
RUN python3 -m ensurepip

RUN apk add --no-cache --virtual .build-deps gcc musl-dev python3-dev; \
    pip3 install awscli python-telegram-bot; \
    apk del .build-deps;

COPY include/telegram.py /usr/bin/telegram
RUN chmod +x /usr/bin/telegram
COPY include/wait-for-it.sh /usr/bin/wait-for-it.sh
RUN chmod +x /usr/bin/wait-for-it.sh