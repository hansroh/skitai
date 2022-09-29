FROM hansroh/aws

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL title="Skitai Package Group Development"
LABEL author="hansroh"
LABEL version="1.0"

RUN apt update
RUN apt install -y python3-pip

RUN pip3 install -U pip
RUN pip3 install -U django psycopg2-binary

COPY tools/docker/requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt && rm -f /requirements.txt

COPY tests/requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt && rm -f /requirements.txt

# install selenium --------------------
RUN apt update && apt install -y wget gnupg unzip curl
RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list
RUN wget https://dl.google.com/linux/linux_signing_key.pub; \
    apt-key add linux_signing_key.pub; \
    rm linux_signing_key.pub
RUN apt update && apt install -y google-chrome-stable
RUN pip3 install -U chromedriver-autoinstaller selenium lxml cssselect html5lib pytest requests

WORKDIR /home/ubuntu/libs/skitai
EXPOSE 5000
CMD [ "/bin/bash" ]
