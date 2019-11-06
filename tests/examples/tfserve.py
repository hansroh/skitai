import skitai
import tfserver
import tensorflow as tf
import os
import sys

def load_latest_model (model_name, subdir = None, per_process_gpu_memory_fraction = 0.03):    
    loc = os.path.normpath(subdir)    
    if not os.path.isdir (loc) or not os.listdir (loc):
        return
    version = max ([int (ver) for ver in os.listdir (loc) if ver.isdigit () and os.path.isdir (os.path.join (loc, ver))])    
    model_path = os.path.join (loc, str (version))
    tfconfig = tf.ConfigProto(log_device_placement = False)
    pref.config.tf_models [model_name] = (model_path, tfconfig)    


if __name__ == "__main__":    
    pref = skitai.pref ()
    pref.max_client_body_size = 100 * 1024 * 1024 # 100 MB
    pref.debug = True
    pref.use_reloader = True
    pref.access_control_allow_origin = ["*"]
    pref.config.tf_models = {}
    load_latest_model ("test", skitai.joinpath ("models"), 0.1)
    skitai.mount ("/", tfserver, pref = pref)
    skitai.run (port = 5000, name = "tfms")

