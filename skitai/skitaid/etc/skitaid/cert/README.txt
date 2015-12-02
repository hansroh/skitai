To make certification file:

openssl req -new -newkey rsa:2048 -x509 -keyout server.pem -out server.pem -days 365 -nodes

