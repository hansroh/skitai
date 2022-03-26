#! /bin/bash
if ! echo $(pip3 list) | grep -q "atila"
then
    echo "updating base libraries..."
    pip3 install -U rs4 sqlphile skitai atila atila-vue
fi
./skitaid.py --devel
