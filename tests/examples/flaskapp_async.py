from flaskapp import app

if __name__ == "__main__":
    import skitai

    skitai.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")
    skitai.mount ("/", app)
    skitai.enable_async_services ()
    skitai.run (port = 30371)
