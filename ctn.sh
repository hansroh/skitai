#! /bin/bash

req=$(which "docker-compose")
if [ "$req" == "" ]
then
    echo "installing docker-compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/1.28.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    sudo rm -f /usr/bin/docker-compose && sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
fi

SERVICE="skitai-dev"
if [ "$1" == "boot" ]
then
    docker-compose up -d $2 $3
    docker attach $SERVICE
elif [ "$1" == "shutdown" ]
then
    docker-compose down
elif [ "$1" == "attach" ]
then
    docker attach $SERVICE
else
    docker-compose $1 $2 $3 $4 $5 $6 $7 $8 $9
fi