FROM hansroh/ubuntu:ecs

ENV PYTHONUNBUFFERED=0

WORKDIR /home/ubuntu/app
COPY ./requirements.txt /requirements.txt
RUN apt update; \
    # apt install -y build-essential cmake zlib1g-dev python3-dev; \
    pip3 install -Ur /requirements.txt; \
    pip3 install -U atila-vue; \
    rm -f /requirements.txt;
    # apt purge -y --auto-remove build-essential cmake zlib1g-dev python3-dev; \
    # apt autoremove -y;

COPY ./dep/production.sh ./dep/production.sh
COPY ./pwa ./pwa
COPY ./skitaid.py ./skitaid.py
RUN chown -R ubuntu:ubuntu /home/ubuntu

USER ubuntu
EXPOSE 5000
CMD ["./dep/production.sh"]
