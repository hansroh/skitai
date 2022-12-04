import os
import pytest
import skitai
import json
import requests
from rs4 import pathtool
import pickle
import shutil
import time
import sys

def test_build_model ():
    # if sys.version_info > (3, 8):
    #     return
    try:
        from tfserver import cli
    except ImportError:
        return

    pathtool.mkdir ('tmp/checkpoint')
    serve = "./examples/tfserve.py"
    with skitai.test_client (serve, port = 30371, silent = False) as engine:
        import build_model
        build_model.train ()
        build_model.restore ()
        build_model.deploy ()

        stub = cli.Server ("http://127.0.0.1:30371")
        for i in range (len (build_model.train_xs)):
            resp = stub.predict ('keras', 'predict', x = build_model.train_xs [i:i+1])
            assert resp.y1_classes.shape == (1, 2)
            assert resp.y1.shape  == (1, 2)
            assert resp.y2_scores.shape == (1, 2)
            assert b'true' in resp.y1_classes.tolist () [0]

        resp = stub.predict ('keras', 'predict', x = build_model.train_xs [:3])
        assert resp.y1.shape  == (3, 2)
        assert resp.y1_classes.shape == (3, 2)
        assert resp.y2_scores.shape == (3, 2)

        resp = stub.predict ('keras', 'reduce_mean', x = build_model.train_xs)
        assert resp.y1.shape == (1, 2)
        assert resp.y1_classes.shape == (1, 2)
        assert resp.y2_scores.shape == (1, 2)
        assert b'true' in resp.y1_classes.tolist () [0]

        shutil.rmtree ('tmp')
        shutil.rmtree ('examples/models/keras')


def test_tfserver ():
    # if sys.version_info > (3, 8):
    #     return
    try:
        from tfserver.loaders import TFServer
        from tfserver import cli
        import numpy as np
        import build_model
    except ImportError:
        return

    serve = "./examples/tfserve.py"
    if os.path.isdir ('./examples/models/ex2'):
        shutil.rmtree ('./examples/models/ex2')

    with skitai.test_client (serve, port = 30371, silent = False) as engine:
        resp = engine.post ("/api", data = json.dumps ({'x': build_model.train_xs [:1].tolist ()}), headers = {"Content-Type": "application/json"})
        assert np.array (resp.data ['y1']).shape == (1, 2)
        assert np.array (resp.data ['y2']).shape == (1, 2)

        s = TFServer ("http://127.0.0.1:30371", "ex1")
        resp = s.predict (x = build_model.train_xs [:1])
        assert resp.y1.shape == (1, 2)

        params = {"media": open ('test-all.sh', 'rb')}
        resp = engine.upload ("/models/ex1/media/predict", data = params)
        assert np.array (resp.data["result"]["y1"]).shape == (1, 2)

        params = {"x": build_model.train_xs [:1].tolist ()}
        resp = engine.post ("/models/ex1/predict", data = json.dumps (params), headers = {"Content-Type": "application/json"})
        assert np.array (resp.data["result"]["y1"]).shape == (1, 2)

        params = {"x": build_model.train_xs [:3].tolist ()}
        resp = engine.post ("/models/ex1/predict", data = json.dumps (params), headers = {"Content-Type": "application/json"})
        assert np.array (resp.data["result"]["y1"]).shape == (3, 2)

        params = {"x": build_model.train_xs [:3].tolist (), 'reduce': 'max'}
        resp = engine.post ("/models/ex1/predict", data = json.dumps (params), headers = {"Content-Type": "application/json"})
        assert np.array (resp.data["result"]["y1"]).shape == (1, 2)

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
        assert resp.status_code == 204
        resp = engine.get ("/models/ex2/version")
        assert resp.data ['version'] == 3

        resp = engine.delete ("/models/ex2")
        assert resp.status_code == 204
        resp = engine.get ("/models/ex2/version")
        assert resp.status_code == 404

def test_retina_face_detector ():
    # if sys.version_info > (3, 8):
    #     return
    try:
        import cv2
        from tfserver import cli
    except ImportError:
        return

    serve = "./examples/tfserve.py"
    with skitai.test_client (serve, port = 30371, silent = False) as engine:
        time.sleep (20.)
        img_path = os.path.join ("examples", 'resources', '0_Parade_marchingband_1_379.jpg')
        stub = engine.grpc ()
        for _ in range (3):
            resp = stub.predict ('face-detector', 'predict', x = cv2.imread (img_path))
            assert len (resp.confidence.shape) == 1
            assert resp.box.shape [1] == 4
            assert resp.keypoints.shape [1] == 10
