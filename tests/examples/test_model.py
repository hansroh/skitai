import pytest
import skitai
from tfserver import cli
from tfserver.predutil import TFServer
import numpy as np
import os
import json
import requests

X = [2622, 129, 1856, 2391, 230, 2562, 4028, 3199, 231, 1843, 3789, 905, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
Y = [0.0, 1.0]
SEQLEN = 12

def test_server ():
    with skitai.test_client (os.path.join (os.path.dirname (__file__), "serve.py"), port = 30371, silent = False):
        s = TFServer ("http://127.0.0.1:30371", "test")
        y = s.predict (x = np.array ([X]), seq_length = np.array ([SEQLEN]))
        assert y.shape == (1, 2)

        params = {
                "spec_name": "test",
                "x": [X],
                "seq_length": [SEQLEN]
        }
        resp = requests.post ("http://127.0.0.1:30371/predict", data = json.dumps (params), headers = {"Content-Type": "application/json"})
        assert np.array (resp.json ()["result"]["y"]).shape == (1, 2)
