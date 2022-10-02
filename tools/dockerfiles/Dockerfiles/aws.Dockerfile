FROM hansroh/ecs:latest
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL title="Ubuntu AWS Like Environment"
LABEL author="hansroh"
LABEL version="1.0"

COPY scripts/development.sh /development.sh
RUN /bin/bash /development.sh && rm -f /development.sh

COPY scripts/terraform.sh /terraform.sh
RUN /bin/bash /terraform.sh && rm -f /terraform.sh

CMD [ "/bin/bash" ]
