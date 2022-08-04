import skitai
import confutil
import pprint
import re
import sys

def test_error_handler (app, capsys):
    @app.route ("/")
    def index (context, limit):
        return ""

    @app.route ("/")
    def index (context, limit, **DATA):
        if context.request.method == "POST":
            assert DATA ['id']
        return 'OK'

    captured = capsys.readouterr ()
    #assert captured.out.find ('def index is already defined') > -1
