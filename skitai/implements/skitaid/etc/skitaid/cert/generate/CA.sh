;/usr/lib/ssl/openssl.cnf
;default days = 7300 

mkdir demoCA
mkdir demoCA/private
mkdir demoCA/certs
mkdir demoCA/crl
mkdir demoCA/newcerts

echo "01" > demoCA/crlnumber
touch demoCA/index.txt

openssl req -new -keyout demoCA/private/cakey.pem -out demoCA/careq.pem
openssl ca -create_serial -out demoCA/cacert.pem -days 36500 -batch -keyfile demoCA/private/cakey.pem -selfsign -extensions v3_ca -infiles demoCA/careq.pem
