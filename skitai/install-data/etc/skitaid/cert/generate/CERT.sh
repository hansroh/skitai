openssl req -new -keyout newkey.pem -out newreq.pem 
openssl ca -policy policy_anything -out newcert.pem -infiles newreq.pem

cp newreq.pem ca.pem
cp newcert.pem server.pem
cat newkey.pem >> server.pem

rm new*
