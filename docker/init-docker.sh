sudo pg_ctlcluster 12 main start

sudo su - postgres -c "psql -c \"drop database if exists skitai;\""
sudo su - postgres -c "psql -c \"create database skitai;\""
sudo su - postgres -c "psql -c \"create user skitai with encrypted password '12345678';\""
sudo su - postgres -c "psql -c \"grant all privileges on database skitai to skitai;\""

cd ~/libs/skitai
cd benchmark
sudo pip3 install -Ur requirements.txt
python3 bench/manage.py migrate
python3 bench/init_db.py

cd ../tests
sudo pip3 install -Ur requirements.txt

cd "${HOME}/libs"
if [ ! -d "${HOME}/libs/atila" ]
then
    git clone git@gitlab.com:skitai/atila.git
fi
if [ ! -d "${HOME}/libs/rs4" ]
then
    git clone git@gitlab.com:skitai/rs4.git
fi
if [ ! -d "${HOME}/libs/sqlphile" ]
then
    git clone git@gitlab.com:skitai/sqlphile.git
fi
if [ ! -d "${HOME}/libs/delune" ]
then
    git clone git@gitlab.com:atila-ext/delune.git
fi
if [ ! -d "${HOME}/libs/atila-vue" ]
then
    git clone git@gitlab.com:atila-ext/atila-vue.git
fi
if [ ! -d "${HOME}/libs/tfserver" ]
then
    git clone git@gitlab.com:tfserver/tfserver.git
fi
if [ ! -d "${HOME}/libs/dnn" ]
then
    git clone git@gitlab.com:tfserver/dnn.git
fi

cd ~/libs/rs4 && pip3 install --no-deps -e .
cd ~/libs/sqlphile && pip3 install --no-deps -e .
cd ~/libs/skitai && pip3 install --no-deps -e .
cd ~/libs/atila && pip3 install --no-deps -e .
cd ~/libs/atila-vue && pip3 install --no-deps -e .
cd ~/libs/delune && pip3 install --no-deps -e .
cd ~/libs/dnn && pip3 install --no-deps -e .
cd ~/libs/tfserver && pip3 install --no-deps -e .
