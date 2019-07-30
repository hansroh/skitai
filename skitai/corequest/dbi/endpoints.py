import sqlite3
import psycopg2
import redis
import pymongo
from skitai import DB_SQLITE3, DB_PGSQL, DB_REDIS, DB_MONGODB
import multiprocessing

CPU_COUNT = multiprocessing.cpu_count ()

def make_endpoints (dbtype, from_list):      
    endpoints = []        
    for server, db, auth in from_list:
        user, password = "", ""
        if auth:
            if len (auth) == 2:
                user, password = auth
            else:
                user = auth [0]    
        if isinstance (server, str):
            try: 
                host, port = server.split (":", 1)
            except ValueError:
                host, port = server, None
        else:
             host, port = server
        
        kargs = {}
        if port: kargs ["port"] = port
        if password: kargs ["password"] = password
        
        if dbtype == DB_SQLITE3:
            conn = sqlite3.connect (host)

        elif dbtype == DB_PGSQL:
            if user: kargs ["user"] = user
            conn = psycopg2.connect (host = host, database = db, **kargs)            

        elif dbtype == DB_REDIS:
            conn = redis.Redis (host = host, port = port, db = db)
        
        elif dbtype == DB_MONGODB:            
            if user: kargs ["username"] = user
            conn = pymongo.MongoClient (host = host, **kargs)

        endpoints.append (conn)
    return endpoints

def restore (conns):
    for conn in conns:
        conn.close ()
