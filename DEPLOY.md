Pipelining template with Gitlab nd AWS.

# Preparation
## Secret Key Name for Gitlab Registry

- Make access token has API and registry write permissions or make [deploy token](https://docs.gitlab.com/ee/user/project/deploy_tokens/index.html)
- Visit [AWS Secrets Manager
](https://ap-northeast-1.console.aws.amazon.com/secretsmanager/home?region=ap-northeast-1#!/listSecrets/)
- Create password with etc type, and edit by text
```json
{
  "username": "username",
  "password": "password"
}
```

## Service Domain
- Create route53 zone with your domain

## S3 Bucket For Saving .tfstate
- Edit all backend option of declares.tf

## AWS API Key

Required Permissions
- AmazonECSTaskExecutionRolePolicy
- AutoScalingFullAccess
- AmazonEC2FullAccess
- ElasticLoadBalancingFullAccess
- AmazonS3FullAccess
- AmazonECS_FullAccess
- AmazonRoute53FullAccess
- AWSCertificateManagerFullAccess
- SecretsManagerReadWrite
- IAMFullAccess

## Optionally Telegram Bot
- Create telegram bot and get token
- Add bot to your project chat room
- Get chat room ID


# Setup Gitlab CI/CD

## Environment Variables
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_DEFAULT_REGION
- TELEGRAM_TOKEN (optional)
- TELEGRAM_CHAT_ID (optional)

## Install Terraform and Configuring AWS
```shell
RUN wget --quiet -O - https://apt.releases.hashicorp.com/gpg | apt-key add -
RUN apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
RUN apt update && apt install -y terraform
```

Then set AWS crednetial.
```shell
export AWS_ACCESS_KEY_ID=<value>
export AWS_SECRET_ACCESS_KEY=<value>
export AWS_DEFAULT_REGION=<value>
```


# Make Skitai App

## Edit Start Script
```python
# skitaid.py
# service name must be specified
skitai.run (ip = "0.0.0.0", port = 5000, name = "myservice")
```

Then create base deploy scripts.
```
./skitaid.py --autoconf
```

Now you get `dep` directory and `.gitlab-ci.yml` and `ctn.sh`.


# Terra Forming

Please review all `.tf` files before applying especially terraform backend setting.

## Creating VPC, DNS Records, Certification and Load Balancer For ECS Cluster
```shell
cd cloud_infra
terraform init
terraform apply
```


## Creating ECS Cluster and Service Roles
```shell
cd ../ecs_cluster
terraform init
terraform apply
```


## Creating ECS Task Definition and Service
```shell
cd ..
terraform init

terraform workspace new qa
terraform apply
terraform workspace new production
terraform apply
```


# Gitlab CI/CD Ppipeline

## Test Stage

You need `tests/test-all.sh` script.
```shell
git checkout -b test
git push origin test
```
## QA Deploy

```shell
git checkout -b qa
git merge test
git push origin qa
```

## Production Deploy
```shell
git checkout -b master
git merge qa
git push origin master
```