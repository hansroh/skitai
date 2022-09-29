
FROM hansroh/ubuntu:aws

ENV PYTHONUNBUFFERED=0

COPY requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt && rm -f /requirements.txt

COPY tests/requirements.txt /requirements.txt
COPY tests/install.sh /install.sh
RUN /install.sh && rm -f /requirements.txt /install.sh

USER ubuntu
WORKDIR /home/ubuntu/app
EXPOSE 5000
<<<<<<< HEAD:tests/examples/autoconf/dep/production.Dockerfile
CMD ["./dep/production.sh"]
=======
>>>>>>> 2c4ca2cdbd9a51dc4fa7c01771ef1ab2bb23bd05:skitai/wastuff/templates/dep/devel.Dockerfile
