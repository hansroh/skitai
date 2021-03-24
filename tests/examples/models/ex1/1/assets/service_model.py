from tfserver import service_models

# servicer ---------------------------------------
class Model (service_models.Model):
    def preprocess (self, wav):
        assert isinstance (wav, str)
        return [(0.1, 0.2, 0.6)]


# load ---------------------------------------
def load (model_path, **config):
    model = Model ()
    model.load (model_path, **config)
    return model
