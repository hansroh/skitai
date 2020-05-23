pip3 install -Us requirements.txt
python3 bench/manage.py migrate
python3 bench/manage.py makemigrations
python3 bench/manage.py migrate
pytho3 init_db.py
