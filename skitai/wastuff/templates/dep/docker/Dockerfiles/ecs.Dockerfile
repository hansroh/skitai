FROM python:3.7-slim
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL title="ECS Deployment"
LABEL author="hansroh"
LABEL version="1.0"

WORKDIR /
ENV LC_ALL=C.UTF-8

RUN apt update
RUN apt install -y sudo wget
RUN python3 -V
RUN pip3 -V

COPY include/wait-for-it.sh /usr/bin/wait-for-it.sh
RUN chmod +x /usr/bin/wait-for-it.sh

RUN adduser --disabled-password --shell /bin/bash --gecos "ubuntu" ubuntu
RUN adduser ubuntu sudo
RUN echo 'ubuntu ALL=NOPASSWD: ALL' >> /etc/sudoers

CMD [ "/bin/bash" ]
