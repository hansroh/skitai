# Download Source
```shell
mkdir -p ~/libs
cd ~/libs
git clone git@gitlab.com:skitai/skitai.git
```

# Creating Docker Image
```shell
cd skitai
docker-compose up -d --build
docker attach skitai
```

# Install Libraries as Development Mode
```shell
./tools/docker/install-libs.sh
```

# Tests
```shell
cd tests
./test-all.sh
```
