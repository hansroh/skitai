import skitai
import atila
import tensorflow as tf
import os
import sys
import tfserver
import dnn
import numpy as np
from rs4.termcolor import tc

def add_model (model_name, model_path):
    model_path = os.path.normpath (model_path)
    if not os.path.isdir (model_path) or not os.listdir (model_path):
        return
    tfserver.add_model (model_name, model_path)


app = atila.Atila (__name__)

@app.on ('tfserver:model-reloaded')
def on_model_loaded (context, alias):
    app.log ('model {} reloaded and refreshing config'.format (alias))

@app.route ('/api')
def api (context, x):
    pred = tfserver.get_model ('ex1').predict (np.array (x))
    return context.API (y1 = (pred [0].tolist ()), y2 = (pred [0].tolist ()))

@app.before_mount
def before_mount (Context):
    from dnn.processing.image import face
    face.register_to_tfserver ('RETINAFACE')

    base_path = skitai.joinpath ('models')
    add_model ("ex1", os.path.join (base_path, "ex1"))

    keras_model = os.path.join (base_path, "keras")
    if os.path.isdir (keras_model):
        add_model ("keras", keras_model)


if __name__ == "__main__":
    dnn.setup_gpus ()
    with skitai.pref () as pref:
        pref.max_client_body_size = 100 * 1024 * 1024 # 100 MB
        pref.access_control_allow_origin = ["*"]
        skitai.mount ("/", app, pref, name = 'myserver', subscribe = 'tfserver')
        skitai.mount ("/", tfserver, pref)
    skitai.config_executors (workers = 4, process_start_method = 'spawn')
    skitai.run (port = 5000, name = "tfserver")
