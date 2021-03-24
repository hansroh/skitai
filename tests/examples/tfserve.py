import skitai
import atila
import tensorflow as tf
import os
import sys
import tfserver
import dnn

def load_model (model_name, model_path, per_process_gpu_memory_fraction = 0.03):
    model_path = os.path.normpath (model_path)
    if not os.path.isdir (model_path) or not os.listdir (model_path):
        return
    tfserver.add_model (model_name, model_path)


if __name__ == "__main__":
    dnn.setup_gpus ()
    pref = skitai.pref ()
    pref.max_client_body_size = 100 * 1024 * 1024 # 100 MB
    pref.access_control_allow_origin = ["*"]
    load_model ("ex1", skitai.joinpath ("models/ex1"))
    if os.path.isdir (skitai.joinpath ("models/keras")):
        load_model ("keras", skitai.joinpath ("models/keras"))
    skitai.mount ("/", tfserver, pref = pref)
    skitai.run (port = 5000, name = "tfserver")
