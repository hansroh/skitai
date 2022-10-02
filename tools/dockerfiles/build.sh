docker build -t hansroh/dep -f Dockerfiles/dep.Dockerfile .
docker build -t hansroh/dep:dind --build-arg DOCKER_TAG=dind -f Dockerfiles/dep.Dockerfile .
docker build -t hansroh/ecs -f Dockerfiles/ecs.Dockerfile .
docker build -t hansroh/aws -f Dockerfiles/aws.Dockerfile .
docker build -t hansroh/tf2.3 -f Dockerfiles/tf2.3.Dockerfile .
docker build -t hansroh/tf2.6 -f Dockerfiles/tf2.6.Dockerfile .
docker build -t hansroh/pytest -f Dockerfiles/pytest.Dockerfile .

docker push hansroh/dep
docker push hansroh/dep:dind
docker push hansroh/ecs
docker push hansroh/aws
docker push hansroh/tf2.3
docker push hansroh/tf2.6
docker push hansroh/pytest
