terraform workspace select production
terraform destroy -auto-approve
terraform workspace select qa
terraform destroy -auto-approve
cd ecs-cluster && terraform destroy -auto-approve
cd ../cloud-infra && terraform destroy -auto-approve
