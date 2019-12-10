from appfunc import app

if __name__ == "__main__":
  import skitai

  skitai.mount ('/', app)
  skitai.run (name = 'wsgi', address = "127.0.0.1", port = 30371)

