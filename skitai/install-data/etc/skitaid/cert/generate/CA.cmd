REM C:\OpenSSL-Win32\bin\openssl.cfg
REM default days = 7300

mkdir demoCA
mkdir demoCA\private
mkdir demoCA\certs
mkdir demoCA\crl
mkdir demoCA\newcerts

copy /y NUL demoCA\index.txt >NUL
echo off
@echo 01 > demoCA\crlnumber
echo on

C:\OpenSSL-Win32\bin\openssl.exe req -new -keyout demoCA\private\cakey.pem -out demoCA\careq.pem -config C:\OpenSSL-Win32\bin\openssl.cfg
C:\OpenSSL-Win32\bin\openssl.exe ca -create_serial -out demoCA\cacert.pem -days 3650 -batch -keyfile demoCA\private\cakey.pem -selfsign -extensions v3_ca -infiles demoCA\careq.pem



