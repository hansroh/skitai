import skitai
import atila
import tensorflow as tf
import os
import sys
import tfserver
import dnn
import numpy as np

def load_model (model_name, model_path):
    model_path = os.path.normpath (model_path)
    if not os.path.isdir (model_path) or not os.listdir (model_path):
        return
    tfserver.add_model (model_name, model_path)


app = atila.Atila (__name__)

@app.on ('tfserver:model-reloaded')
def on_model_loaded (was, alias):
    app.log ('model {} reloaded and refreshing config'.format (alias))

@app.route ('/api')
def api (was, x):
    pred = tfserver.get_model ('ex1').predict (np.array (x))
    return was.API (y1 = (pred [0].tolist ()), y2 = (pred [0].tolist ()))


if __name__ == "__main__":
    dnn.setup_gpus ()
    with skitai.pref () as pref:
        pref.max_client_body_size = 100 * 1024 * 1024 # 100 MB
        pref.access_control_allow_origin = ["*"]
        load_model ("ex1", skitai.joinpath ("models/ex1"))
        if os.path.isdir (skitai.joinpath ("models/keras")):
            load_model ("keras", skitai.joinpath ("models/keras"))

        skitai.mount ("/", tfserver, pref = pref)
        skitai.mount ("/", app, pref = pref, name = 'myserver', subscribe = 'tfserver')

    skitai.config_executors (workers = 4, process_start_method = 'spawn')
    skitai.run (port = 5000, name = "tfserver")
