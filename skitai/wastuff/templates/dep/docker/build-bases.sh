docker build -t hansroh/ubuntu:dep -f build/dep.docker .
docker build -t hansroh/ubuntu:ecs -f build/ecs.docker .
docker build -t hansroh/ubuntu:aws -f build/aws.docker .
docker build -t hansroh/ubuntu:tf2.3 -f build/tf2.3.docker .
docker build -t hansroh/ubuntu:tf2.6 -f build/tf2.6.docker .

docker push hansroh/ubuntu:dep
docker push hansroh/ubuntu:ecs
docker push hansroh/ubuntu:aws
docker push hansroh/ubuntu:tf2.3
docker push hansroh/ubuntu:tf2.6
