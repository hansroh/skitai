FROM tensorflow/tensorflow:2.6.1-gpu
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL title="Tensorflow 2.6.x For Cuda >= 11.1"
LABEL author="hansroh"
LABEL version="1.0"

WORKDIR /

RUN apt update
RUN apt install -y sudo
RUN adduser --disabled-password --shell /bin/bash --gecos "ubuntu" ubuntu
RUN adduser ubuntu sudo
RUN echo 'ubuntu ALL=NOPASSWD: ALL' >> /etc/sudoers

RUN apt install -y build-essential zlib1g-dev cmake vim git tmux sudo wget
RUN pip3 install -U pip
RUN pip3 install -U jupyter

COPY include/wait-for-it.sh /usr/bin/wait-for-it.sh
RUN chmod +x /usr/bin/wait-for-it.sh

EXPOSE 8888
CMD [ "/bin/bash" ]
