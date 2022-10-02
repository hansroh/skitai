FROM python:3.7-slim
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL title="ECS Deployment"
LABEL author="hansroh"
LABEL version="1.0"

WORKDIR /
ENV LC_ALL=C.UTF-8

COPY scripts/init.sh /init.sh
RUN /bin/bash /init.sh && rm -f /init.sh
RUN pip3 install -U pip

CMD [ "/bin/bash" ]
