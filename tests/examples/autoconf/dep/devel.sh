#! /bin/bash
if ! echo $(pip3 list) | grep -q "skitai"
then
    echo "updating base libraries..."
    echo pip3 install -U skitai
fi
./skitaid.py --devel
