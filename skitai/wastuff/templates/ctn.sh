#! /bin/bash

req=$(which "docker-compose")
if [ "$req" == "" ]
then
    echo "installing docker-compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/1.28.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    sudo rm -f /usr/bin/docker-compose && sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
fi

SERVICE="skitai-dep-dev"
if [ "$1" == "boot" ]
then
    docker-compose -f dep/devel.yml up -d $2 $3
    docker attach $SERVICE
elif [ "$1" == "shutdown" ]
then
    docker-compose -f dep/devel.yml down
elif [ "$1" == "attach" ]
then
    docker attach $SERVICE


elif [ "$1" == "dep" ]
then
    docker-compose -f dep/production.yml up -d $2 $3
elif [ "$1" == "undep" ]
then
    docker-compose -f dep/production.yml down
elif [ "$1" == "test" ]
then
    docker exec -t $CONTAINER_NAME /bin/bash -c "cd tests && sudo ./install.sh && ./test-all.sh"


else
    docker-compose -f dep/devel.yml $1 $2 $3 $4 $5 $6 $7 $8 $9
fi