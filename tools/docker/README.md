# Download Source
```shell
mkdir -p ~/libs
cd ~/libs
git clone git@gitlab.com:skitai/skitai.git
```

# Creating Docker Image
```shell
cd skitai
docker build --tag hansroh/skitai:latest .
```

# Run Container
```shell
docker run -it --name skitai \
    -v /home/ubuntu:home/ubuntu \
    -p 5000:5000 \
    --user ubuntu \
    hansroh/skitai /bin/bash
```

# Initializing Docker
```shell
cd ~/libs/skitai
./tools/docker/init-docker.sh
```

# Tests
```shell
cd ~/libs/skitai/tests
./test-all.sh
```
