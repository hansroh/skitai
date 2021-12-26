docker build -t hansroh/ubuntu:dep -f Dockerfiles/dep.Dockerfile .
docker build -t hansroh/ubuntu:ecs -f Dockerfiles/ecs.Dockerfile .
docker build -t hansroh/ubuntu:aws -f Dockerfiles/aws.Dockerfile .
docker build -t hansroh/ubuntu:tf2.3 -f Dockerfiles/tf2.3.Dockerfile .
docker build -t hansroh/ubuntu:tf2.6 -f Dockerfiles/tf2.6.Dockerfile .

docker push hansroh/ubuntu:dep
docker push hansroh/ubuntu:ecs
docker push hansroh/ubuntu:aws
docker push hansroh/ubuntu:tf2.3
docker push hansroh/ubuntu:tf2.6
