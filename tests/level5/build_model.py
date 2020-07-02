import tensorflow as tf
import numpy as np
from rs4.mltk import metrics, callbacks, losses
from rs4 import pathtool
import shutil
from tfserver import label
import os

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

labels = [label.Label (['true', 'false'], 'truth'), label.Label (['true', 'false'], 'faith')]
validation_data = (train_xs, {"y1": train_ys, "y2": train_ys})

EPOCHS = 10
INIT_LR = 1e-3
BS = 32

def create_model (checkpoint = None):
    x = tf.keras.layers.Input (3, name = 'x')
    h1 = tf.keras.layers.Dense (10, activation='relu') (x)
    y1 = tf.keras.layers.Dense (2, activation='softmax', name = 'y1') (h1)

    h2 = tf.keras.layers.Dense (10, activation='relu') (x)
    y2 = tf.keras.layers.Dense (2, activation='softmax', name = 'y2') (h2)

    model = tf.keras.Model (x, [y1, y2])

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

    model = create_model ()
    save_checkpoint = tf.keras.callbacks.ModelCheckpoint (
        filepath = './tmp/checkpoint/cp.ckpt',
        save_weights_only = True,
        monitor = 'val_y2_accuracy',
        model = 'max',
        save_best_only = True
    )
    model.fit (
        train_xs,
        {"y1": train_ys, "y2": train_ys},
        validation_data = validation_data,
        epochs=EPOCHS, batch_size=BS,
        callbacks = [
            save_checkpoint,
            callbacks.ConfusionMatrixCallback (labels, validation_data),
            tf.keras.callbacks.EarlyStopping(patience=2),
            # tf.keras.callbacks.TensorBoard(log_dir='./logs')
        ]
    )
    model.evaluate (train_xs, train_ys)
    model.predict (train_xs)

def restore ():
    from tfserver import saved_model
    model = create_model ('./tmp/checkpoint/cp.ckpt')
    model.evaluate (train_xs, {"y1": train_ys, "y2": train_ys})
    return model

def deploy (model):
    from tfserver import saved_model
    import os, shutil

    if os.path.exists ('tmp/exported'):
        shutil.rmtree ('tmp/exported')
    inputs, outputs = saved_model.save ('tmp/exported', model, labels = labels)
    print ("* Saved Model")
    print ("  - Inputs")
    for k, v in inputs.items (): print ("    . {}: {}".format (k, v.name))
    print ("  - Outputs")
    for k, v in outputs.items (): print ("    . {}: {}".format (k, v.name))

    resp = saved_model.deploy ('tmp/exported', 'http://127.0.0.1:30371/models/keras/versions/1', overwrite = True)
    print (resp)

if __name__ == '__main__':
    # train ()
    model = restore ()
    deploy (model)
