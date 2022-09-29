FROM hansroh/ubuntu:ecs
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL title="Ubuntu AWS Like Environment"
LABEL author="hansroh"
LABEL version="1.0"

RUN apt install -y build-essential zlib1g-dev cmake vim git tmux wget python3-dev software-properties-common
RUN wget --quiet -O - https://apt.releases.hashicorp.com/gpg | apt-key add -
RUN apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
RUN apt update && apt install -y terraform
RUN pip3 install -U awscli

CMD [ "/bin/bash" ]
