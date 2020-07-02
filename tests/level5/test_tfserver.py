import pytest
import skitai
import os
import json
import requests
from rs4 import pathtool
import pickle

X = [2622, 129, 1856, 2391, 230, 2562, 4028, 3199, 231, 1843, 3789, 905, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
Y = [0.0, 1.0]
SEQLEN = 12

def test_tfserver ():
    serve = "./examples/tfserve.py"
    with skitai.test_client (serve, port = 30371, silent = False) as engine:
        try:
            from tfserver.predutil import TFServer, cli
            import numpy as np
        except ImportError:
            return

        s = TFServer ("http://127.0.0.1:30371", "ex1")
        y = s.predict (x = np.array ([X]), seq_length = np.array ([SEQLEN]))
        assert y.shape == (1, 2)

        with open ('examples/models/fashion/1/assets/fashionX.pik', 'rb') as f:
            testX = pickle.loads (f.read ()) [:3]

        stub = cli.Server ("http://127.0.0.1:30371")
        for i in range (len (testX)):
            resp = stub.predict ('fashion', 'predict', input_1 = testX [i:i+1])
            assert resp.category_output_classes.shape == (1, 4)
            assert resp.color_output.shape  == (1, 3)
            assert resp.category_output_scores.shape == (1, 4)
            assert b'jeans' in resp.category_output_classes.tolist () [0]

        params = {
                "x": [X],
                "seq_length": [SEQLEN]
        }
        resp = engine.post ("/models/ex1/predict", data = json.dumps (params), headers = {"Content-Type": "application/json"})
        assert np.array (resp.data["result"]["y"]).shape == (1, 2)

        resp = engine.get ("/models/ex1/version")
        assert resp.data ['version'] == 1

        resp = engine.get ("/models")
        assert 'ex1' in resp.data ['models']

        resp = engine.get ("/models/ex1")
        assert 'path' in resp.data
        assert 'version' in resp.data
        assert 'labels' in resp.data

        pathtool.zipdir ('examples/models/ex1/model.zip', 'examples/models/ex1/1')
        assert os.path.isfile ('examples/models/ex1/model.zip')

        resp = pathtool.uploadzip (
            'http://127.0.0.1:30371/models/ex2/versions/3',
            'examples/models/ex1/model.zip',
            refresh = True,
            overwrite = True
        )
        assert resp.status_code == 201
        resp = engine.get ("/models/ex2/version")
        assert resp.data ['version'] == 3

        resp = engine.get ("/models")
        assert 'ex2' in resp.data ['models']

        resp = pathtool.uploadzip (
            'http://127.0.0.1:30371/models/ex2/versions/3',
            'examples/models/ex1/model.zip',
            refresh = True
        )
        assert resp.status_code == 409
        resp = engine.get ("/models/ex2/version")
        assert resp.data ['version'] == 3

        resp = pathtool.uploadzip (
            'http://127.0.0.1:30371/models/ex2/versions/4',
            'examples/models/ex1/model.zip',
            refresh = True,
            overwrite = True
        )
        assert resp.status_code == 201
        resp = engine.get ("/models/ex2/version")
        assert resp.data ['version'] == 4

        resp = engine.delete ("/models/ex2/versions/4")
        assert resp.status_code == 204
        resp = engine.get ("/models/ex2/version")
        assert resp.data ['version'] == 3

        resp = engine.patch ("/models/ex2")
        assert resp.status_code == 200
        resp = engine.get ("/models/ex2/version")
        assert resp.data ['version'] == 3

        resp = engine.delete ("/models/ex2")
        assert resp.status_code == 204
        resp = engine.get ("/models/ex2/version")
        assert resp.status_code == 404













