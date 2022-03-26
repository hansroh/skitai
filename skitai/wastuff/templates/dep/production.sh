#! /bin/bash

# /var/www/pub must be created on ecs task definition
sudo chown -R ubuntu:ubuntu /home/ubuntu
sudo chown -R ubuntu:ubuntu /var/www/pub
mkdir -p ~/.skitai/stt-api
ln -s /var/www/pub ~/.skitai/stt-api/pub
./skitaid.py --disable-static
