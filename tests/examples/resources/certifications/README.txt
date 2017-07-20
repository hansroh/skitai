; Create the Server Key and Certificate Signing Request
sudo openssl genrsa -des3 -out server.key 2048
sudo openssl req -new -key server.key -out server.csr
  
; Remove the Passphrase If you need
sudo cp server.key server.key.org
sudo openssl rsa -in server.key.org -out server.key
  
; Sign your SSL Certificate
sudo openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

  
skitai.mount ('/', app)
skitai.enable_ssl ('server.crt', 'server.key', 'your pass phrase')
skitai.run (port = 443)


