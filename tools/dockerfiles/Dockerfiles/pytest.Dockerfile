FROM hansroh/ecs:latest
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL title="Selenium Test Docker"
LABEL author="hansroh"
LABEL version="1.0"

RUN apt update && apt install -y wget gnupg unzip curl
RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list
RUN wget https://dl.google.com/linux/linux_signing_key.pub; \
    apt-key add linux_signing_key.pub; \
    rm linux_signing_key.pub
RUN apt update && apt install -y google-chrome-stable
RUN pip3 install -U chromedriver-autoinstaller selenium lxml cssselect html5lib pytest requests
RUN python3 -c "import chromedriver_autoinstaller as ca; ca.install ()"

CMD [ "/bin/bash" ]
