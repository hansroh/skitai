import sqlphile as sp
import os

auth, netloc = os.environ ['MYDB'].split ("@")
user, passwd = auth.split (":")
host, database = netloc.split ("/")

with sp.pg2.open (database, user, passwd, host) as db:
    for i in range (10000):
        db.execute ('''
            INSERT INTO foo (tx_id, from_left, to_left, amount, from_address, to_address, detail, created_at, from_wallet_id, to_wallet_id, valid, block_number, errcode, errmsg) VALUES ('0x30adf71db10342033363b7e8b64d244af37468d0b7f2ckkd4085f950ff{}', 2993533506970928, 1106829, 1, '0xad62eed293fa76f0bkk5ceee7cb0fe31d72f74a7', '0xd072c77992132e334kkcb02135e37b7af12dea46', 'ReturnTx', '2019-07-29 15:27:30.539618+09', 8, 67, 'notyet', 55543, NULL, NULL);
        '''.format (str (i).zfill (9)))
        if i % 100 == 0:
            db.commit ()
    db.commit ()
