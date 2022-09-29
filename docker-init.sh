#!/bin/bash

cd ~/libs/skitai/benchmark/bench
./manage.py migrate
python3 init_db.py
cd ~/libs/skitai/tools/docker
./install-libs.sh
