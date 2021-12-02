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
