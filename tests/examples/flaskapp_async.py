from flaskapp import app

if __name__ == "__main__":
    import skitai

    skitai.mount ("/", app)
    skitai.run (port = 30371)
