pip3 install -Us requirements.txt
python3 bench/manage.py migrate
python3 bench/manage.py makemigrations
python3 bench/manage.py migrate
python3 bench/init_db.py
