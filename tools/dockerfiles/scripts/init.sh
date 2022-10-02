apt update
apt install -y sudo wget

adduser --disabled-password --shell /bin/bash --gecos "ubuntu" ubuntu
adduser ubuntu sudo
echo 'ubuntu ALL=NOPASSWD: ALL' >> /etc/sudoers

wget -O /usr/bin/wait-for-it.sh -q https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh
chmod +x /usr/bin/wait-for-it.sh
