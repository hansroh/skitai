FROM hansroh/ubuntu:aws

ENV PYTHONUNBUFFERED=0

WORKDIR /home/ubuntu/app
COPY requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt && rm -f /requirements.txt
RUN pip3 install -U atila-vue

COPY ./dep ./dep
COPY ./pwa ./pwa
COPY ./skitaid.py ./skitaid.py

EXPOSE 5000
ENTRYPOINT ["./dep/production.sh"]
