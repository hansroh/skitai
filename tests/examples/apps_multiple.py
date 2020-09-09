from atila import Atila

if __name__ == "__main__":
    import skitai
    skitai.mount ("/", 'statics')
    skitai.mount ("/", "app.py")
    skitai.mount ("/", "app2.py")
    skitai.mount ("/", 'rpc2.py')
    skitai.mount ("/myrpc", 'rpc2.py', name = 'myrpc')
    skitai.mount ("/", 'auth.py')
    skitai.run (
        address = "0.0.0.0",
        port = 30371
    )
