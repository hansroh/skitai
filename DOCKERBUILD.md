# Create Docker Container
```shell
docker run -it --name skitai \
    -p 5000:5000 -p 5001:5001 \
    -v /home/ubuntu:/home/ubuntu -v /mnt:/mnt \
    --user ubuntu
    hansroh/ubuntu:aws /bin/bash
```


# Install Sources
## Skitai
```shell
cd ~
mkdir -p libs $$ cd libs
git clone git@gitlab.com:skitai/skitai.git
git clone git@gitlab.com:skitai/atila.git
git clone git@gitlab.com:skitai/rs4.git
git clone git@gitlab.com:skitai/sqlphile.git
git clone git@gitlab.com:atila-ext/atila-vue.git
```

```shell
sudo pip3 install -U pip tqdm colorama requests jinja2 h2 psutil setproctitle

cd ~/libs/rs4 && pip3 install --no-deps -e .
cd ~/libs/sqlphile && pip3 install --no-deps -e .
cd ~/libs/skitai && pip3 install --no-deps -e .
cd ~/libs/atila && pip3 install --no-deps -e .
cd ~/libs/atila-vue && pip3 install --no-deps -e .
```

## Data Science
```shell
cd ~
mkdir -p libs $$ cd libs
git clone git@gitlab.com:atila-ext/delune.git
git clone git@gitlab.com:tfserver/tfserver.git
git clone git@gitlab.com:tfserver/dnn.git
```

```shell
sudo apt install zlib1g-dev libjpeg-dev libssl-dev wget
sudo pip3 install -U \
    numpy scikit-learn future networkx hyperopt protobuf \
    dill webrtcvad exif fdet torchvision torch

cd ~/libs/delune && pip3 install --no-deps -e .
cd ~/libs/dnn && pip3 install --no-deps -e .
cd ~/libs/tfserver && pip3 install --no-deps -e .
```

# Install PostgreSQL 12
```shell
sudo apt install wget
sudo echo "deb http://apt.postgresql.org/pub/repos/apt/ bionic-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update && sudo apt install postgresql-12
```

## Edit .bashrc
```shell
export LANG=C.UTF-8
export "skitai:12345678@localhost/skitai"
```

## Create User and Database
```shell
sudo su - postgres
psql
create user skitai password '12345678' superuser;
create database skitai owner skitai;
\q
```

Exit and migrate and generate data.
```shell
cd ~/libs/skitai/benchmark
./install.sh
```
