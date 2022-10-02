rm -rf ~/libs/skitai/skitai/wastuff/templates
mkdir -p ~/libs/skitai/skitai/wastuff/templates

cp -r dep ~/libs/skitai/skitai/wastuff/templates/
cp .gitlab-ci.yml ~/libs/skitai/skitai/wastuff/templates/
cp ctn.sh ~/libs/skitai/skitai/wastuff/templates/

# readme
rm -f ~/libs/skitai/DEPLOY.md
cp README.md ~/libs/skitai/DEPLOY.md

# remove unneeds
rm -rf ~/libs/skitai/skitai/wastuff/templates/dep/terraform/experiments
