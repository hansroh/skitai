C:\OpenSSL-Win32\bin\openssl.exe req -new -keyout newkey.pem -out newreq.pem -days 1095
C:\OpenSSL-Win32\bin\openssl.exe ca -policy policy_anything -out newcert.pem -infiles newreq.pem
copy newreq.pem ca.pem
copy newcert.pem+newkey.pem server.pem
del /y newcert.pem
del /y newreq.pem
del /y newkey.pem

