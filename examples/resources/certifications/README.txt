==================================================
To make certification file:
==================================================

openssl req -new -newkey rsa:2048 -x509 -keyout cert.pem -out cert.pem -days 365 -nodes

Then save cert.pem to /etc/skitaid/cert or C:\skitaid\etc\cert



==================================================
To make CA authorized certification file: 
==================================================

Step I. Create self singed root CA
------------------------------------

edit /usr/lib/ssl/openssl.cnf if need.

mkdir demoCA
mkdir demoCA/private
mkdir demoCA/certs
mkdir demoCA/crl
mkdir demoCA/newcerts

echo "01" > demoCA/crlnumber
touch demoCA/index.txt

openssl req -new -keyout demoCA/private/cakey.pem -out demoCA/careq.pem
openssl ca -create_serial -out demoCA/cacert.pem -days 365 -batch -keyfile demoCA/private/cakey.pem -selfsign -extensions v3_ca -infiles demoCA/careq.pem




Step II. Generate your certification
------------------------------------

openssl req -new -keyout key.pem -out req.pem 
openssl ca -policy policy_anything -out server.pem -infiles req.pem




Step III. Merge 3 files
------------------------------------

merge key.pem, req.pem, server.pem like this:

-----BEGIN ENCRYPTED PRIVATE KEY-----
MIIFDjBABgkqhkiG9w0BBQ0wMzAbBgkqhkiG9w0BBQwwDgQI84xb8w7/BGUCAggA
MBQGCCqGSIb3DQMHBAg9BFx5uBWmbQSCBMjVzTF8jSfMDaiUU8i2bWkZV+EaseFm
...
-----END ENCRYPTED PRIVATE KEY-----
-----BEGIN CERTIFICATE REQUEST-----
MIICozCCAYsCAQAwXjELMAkGA1UEBhMCVVMxDzANBgNVBAgMBkFsYXNrYTEQMA4G
A1UEBwwHV2FzaWxsYTEVMBMGA1UECgwMU2tpdGFpIEdyb3VwMRUwEwYDVQQDDAwq
...
-----END CERTIFICATE REQUEST-----
-----BEGIN CERTIFICATE-----
MIIDwDCCAqigAwIBAgIJAKdoxifDhlqfMA0GCSqGSIb3DQEBCwUAMGQxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
...
-----END CERTIFICATE-----


Then save cert.pem to /etc/skitaid/cert or C:\skitaid\etc\cert



