import tensorflow as tf
import numpy as np
import dnn
from dnn import metrics, callbacks, losses
from rs4 import pathtool
import shutil
from tfserver import label, datasets
import os
import glob
from tfserver import service_models

train_xs = np.array ([
    (0.1, 0.2, 0.6),
    (0.3, 0.6, 0.7),
    (0.2, 0.9, 0.3),
    (0.3, 0.9, 0.1),
])

train_ys = np.array ([
    (1.0, 0),
    (0, 1.0),
    (1.0, 0),
    (0, 1.0),
])

dataset = tf.data.Dataset.from_tensor_slices ((train_xs, (train_ys, train_ys))).batch (2).repeat ()
validation_data = tf.data.Dataset.from_tensor_slices ((train_xs, (train_ys, train_ys))).batch (1)
labels = [label.Label (['true', 'false'], 'truth'), label.Label (['true', 'false'], 'faith')]

dss = datasets.Datasets (2, dataset, validation_data, labels = labels)
EPOCHS = 30
INIT_LR = 1e-3
BS = 32

def create_model (checkpoint = None):
    x = tf.keras.layers.Input (3, name = 'x')

    h = tf.keras.layers.Dense (9, activation='relu') (x)
    h = tf.keras.layers.Dense (4, activation='relu') (h)
    y1_ = tf.keras.layers.Dense (2, activation='softmax', name = 'y1') (h)

    h = tf.keras.layers.Dense (8, activation='relu') (x)
    h = tf.keras.layers.Dense (6, activation='relu') (h)
    y2_ = tf.keras.layers.Dense (2, activation='softmax', name = 'y2') (h)

    model = tf.keras.Model (x, [y1_, y2_])

    optimizer = tf.keras.optimizers.Adam(lr=INIT_LR, decay=INIT_LR / EPOCHS)
    model.compile (
        optimizer=optimizer,
        loss = ['categorical_crossentropy', losses.focal_losses.categorical_focal_loss ()],
        metrics = ['accuracy', 'categorical_accuracy']
    )
    checkpoint and model.load_weights (checkpoint)
    model.summary()
    return model


def numpy_metric (y_true, y_pred, logs, name = None):
    logs ['val_{}_acc'.format (name)] = np.mean (np.argmax (y_true, axis = 1) == np.argmax (y_pred, axis = 1))
    return 'my {} log line'.format (name)


def train ():
    model = create_model ()
    model.fit (
        dss.trainset,
        validation_data = dss.validset,
        epochs=EPOCHS,
        steps_per_epoch = dss.steps,
        callbacks = dnn.callbacks.compose (
            './tmp', dss,
            custom_metric = numpy_metric,
            monitor = ('val_y1_accuracy', 'max'),
            early_stop = (20, "val_y1_accuracy", "max"),
            learning_rate = (0.001, 0.98),
            enable_logging = False,
            reset_train_dir = True
        )
    )
    model.evaluate (dss.validset)
    if os.path.exists ('tmp/exported'):
        shutil.rmtree ('tmp/exported')
    service_models.Model ().save ('tmp/exported', model, dss)

def restore ():
    version = service_models.get_latest_version ('tmp/exported')
    dss = datasets.load ('tmp/exported/{}/assets'.format (version), testset = True)
    best = sorted (glob.glob (os.path.join ('tmp/checkpoint', '*.ckpt.index'))) [-1]
    model = create_model (best [:-6])
    model.evaluate (dss.testset)
    model.predict (dss.testset_as_numpy () [0])
    return model

def deploy ():
    from sklearn.metrics import f1_score
    import numpy as np
    import os, shutil

    model = service_models.Model ()
    model.load ('tmp/exported', testset = True)

    x_test, y_true = model.ds.testset_as_numpy ()
    y1_pred = np.argmax (model.predict (x_test) [0], axis = 1)
    f1_1 = f1_score (np.argmax (y_true [0], axis = 1), y1_pred, average = 'weighted')

    resp = model.deploy ('http://127.0.0.1:30371/models/keras', overwrite = True)
    print (resp)


if __name__ == '__main__':
    train ()
    restore ()
    deploy ()
