#!/usr/bin/python

from flask import Flask
app = Flask(__name__)
app.debug = True
app.use_reloader = True

@app.route('/')
def hello_world():
    return 'pong4sdfdd55'

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002)

