import tensorflow as tf
import numpy as np
from dnn import metrics, callbacks, losses
from rs4 import pathtool
import shutil
from tfserver import label, datasets
import os
import glob

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

dataset = tf.data.Dataset.from_tensor_slices ((train_xs, {"y1": train_ys, "y2": train_ys})).batch (2).repeat ()
validation_data = tf.data.Dataset.from_tensor_slices ((train_xs, {"y1": train_ys, "y2": train_ys})).batch (1)
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

def train ():
    if os.path.exists ('tmp/checkpoint'):
        shutil.rmtree ('tmp/checkpoint')
    pathtool.mkdir ('tmp/checkpoint')
    dss.save ('tmp/checkpoint/assets')

    model = create_model ()
    save_checkpoint = tf.keras.callbacks.ModelCheckpoint (
        filepath = './tmp/checkpoint/{epoch:04d}.acc-{val_y1_accuracy:.2f}.ckpt',
        save_weights_only = True,
        monitor = 'val_y1_accuracy',
        model = 'max',
        save_best_only = True
    )
    model.fit (
        dss.trainset,
        validation_data = dss.validset,
        epochs=EPOCHS,
        steps_per_epoch = dss.steps,
        callbacks = [
            save_checkpoint,
            callbacks.ConfusionMatrixCallback (dss.labels, dss.validset),
            tf.keras.callbacks.EarlyStopping(patience=2),
            # tf.keras.callbacks.TensorBoard(log_dir='./logs')
        ]
    )
    model.evaluate (dss.validset)

def restore ():
    from tfserver import saved_model

    dss = datasets.load ('tmp/checkpoint/assets')
    best = sorted (glob.glob (os.path.join ('tmp/checkpoint', '*.ckpt.index'))) [-1]
    model = create_model (best [:-6])
    model.evaluate (dss.testset)
    model.predict (dss.testset_as_numpy () [0])

    return model

def deploy (model):
    from tfserver import saved_model, datasets
    from sklearn.metrics import f1_score
    import numpy as np
    import os, shutil

    if os.path.exists ('tmp/exported'):
        shutil.rmtree ('tmp/exported')

    saved_model.save ('tmp/exported', model, labels = labels, assets_dir = 'tmp/checkpoint/assets')
    model_s = saved_model.load ('tmp/exported')
    dss = datasets.load ( 'tmp/checkpoint/assets')
    x_test, y_true = dss.testset_as_numpy ()

    y1_pred = np.argmax (model.predict (x_test) [0], axis = 1)
    f1_1 = f1_score (np.argmax (y_true ['y1'], axis = 1), y1_pred, average = 'weighted')

    y1_pred = np.argmax (model_s.ftest (x_test).y1, axis = 1)
    f1_2 = f1_score (np.argmax (y_true ['y1'], axis = 1), y1_pred, average = 'weighted')
    assert f1_1 == f1_2

    resp = saved_model.deploy ('tmp/exported', 'http://127.0.0.1:30371/models/keras/versions/1', overwrite = True)
    print (resp)

if __name__ == '__main__':
    train ()
    model = restore ()
    deploy (model)
