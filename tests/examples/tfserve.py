import skitai
import atila
import tensorflow as tf
import os
import sys
import tfserver

def load_latest_model (model_name, subdir = None, per_process_gpu_memory_fraction = 0.03):
    loc = os.path.normpath(subdir)
    if not os.path.isdir (loc) or not os.listdir (loc):
        return
    version = max ([int (ver) for ver in os.listdir (loc) if ver.isdigit () and os.path.isdir (os.path.join (loc, ver))])
    model_path = os.path.join (loc, str (version))
    tfserver.add_model (model_name, model_path, 0.1)


if __name__ == "__main__":
    pref = skitai.pref ()
    pref.max_client_body_size = 100 * 1024 * 1024 # 100 MB
    pref.access_control_allow_origin = ["*"]
    load_latest_model ("ex1", skitai.joinpath ("models/ex1"), 0.1)
    load_latest_model ("fashion", skitai.joinpath ("models/fashion"), 0.1)
    skitai.mount ("/", tfserver, pref = pref)
    skitai.run (port = 5000, name = "tfms")
