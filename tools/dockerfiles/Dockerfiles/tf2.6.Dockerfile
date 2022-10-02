FROM tensorflow/tensorflow:2.6.1-gpu
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL title="Tensorflow 2.6.x For Cuda >= 11.1"
LABEL author="hansroh"
LABEL version="1.0"

WORKDIR /

COPY scripts/init.sh /init.sh
RUN /bin/bash /init.sh && rm -f /init.sh

COPY scripts/development.sh /development.sh
RUN /bin/bash /development.sh && rm -f /development.sh

RUN pip3 install -U jupyter

EXPOSE 8888
CMD [ "/bin/bash" ]
