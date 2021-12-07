#! /bin/bash

req=$(which "docker-compose")
if [ "$req" == "" ]
then
    echo "installing docker-compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/1.28.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    sudo rm -f /usr/bin/docker-compose && sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
fi

SERVICE="stt-api-dev"
if [ "$1" == "bash" ]
then
    docker exec -it $SERVICE /bin/bash
elif [ "$1" == "boot" ]
then
    docker-compose -f dep/devel.yml up -d
    docker attach $SERVICE
elif [ "$1" == "attach" ]
then
    docker attach $SERVICE
elif [ "$1" == "test" ]
then
    docker exec -it $SERVICE /bin/bash -c "cd tests && ./test-all.sh"
elif [ "$1" == "exec" ]
then
    docker exec -it $SERVICE $2 $3 $4 $5 $6 $7 $8 $9
else
    docker-compose -f dep/devel.yml $1 $2 $3 $4 $5 $6 $7 $8 $9
fi
