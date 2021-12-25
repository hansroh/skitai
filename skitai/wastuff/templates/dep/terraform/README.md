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


# Install Terraform and Configuring AWS
```shell
RUN wget --quiet -O - https://apt.releases.hashicorp.com/gpg | apt-key add -
RUN apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
RUN apt update && apt install -y terraform
```

```shell
export AWS_ACCESS_KEY_ID=<value>
export AWS_SECRET_ACCESS_KEY=<value>
export AWS_DEFAULT_REGION=<value>
```


# Terra Forming

Please review all `.tf` files before applying.

## Creating VPC, Certification and Load Balancer
```shell
cd cloud_infra
terraform init
terraform apply
```

## Creating ECS Cluster
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
