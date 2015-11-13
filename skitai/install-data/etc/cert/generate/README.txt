[Win32]

install Win32OpenSSL-1_0_1g.exe
install M2Crypto-0.21.1.win32-py2.7.msi

run CA.cmd
run CERT.cmd
copy 
ca.pem, server.pem to proper location

[Linux]

run CA.sh
run CERT.sh
cp ca.pem, server.pem to proper location

