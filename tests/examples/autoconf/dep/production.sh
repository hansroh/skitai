#! /bin/bash
sudo chown -R ubuntu:ubuntu /home/ubuntu
sudo chown -R ubuntu:ubuntu /var/www/pub
mkdir -p ~/.skitai/stt-api
ln -s /var/www/pub /home/ubuntu/.skitai/testapp/pub
./skitaid.py --disable-static
