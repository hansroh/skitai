from aquests.dbapi import synsqlite3, request, asynpsycopg2   
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, select, MetaData, Table
from sqlalchemy import Column, Integer, String
from skitai import DB_SQLITE3, DB_PGSQL

Base = declarative_base()

class Stocks (Base):
  __tablename__ = 'stocks'
  id = Column(Integer, primary_key=True)
  date = Column(String(255))
  trans = Column(String(255))
  symbol = Column(String(255))
  qty = Column(Integer)
  price = Column(Integer)
  
stocks = Stocks.__table__

metadata = MetaData()
stocks2 = Table ('stocks', metadata,
   Column('id', Integer, primary_key=True),
   Column('date', String(255)),
   Column('trans', String(255)),
   Column('symbol', String(255)),
   Column('qty', Integer),
   Column('price', Integer)
)


def callback1 (resp):
    assert resp.data [0].id == 1.0
 
def callback2 (resp):
    assert not resp.data

def callback3 (resp):
    assert len (resp.data) >= 2

def callback4 (resp):
    assert resp.data [0].symbol == "BIX"

def callback5 (resp):
    assert resp.code == 500
        
def test_str (dbpath, log):
    f = synsqlite3.SynConnect (dbpath, logger = log.get ("app"))
    
    statement = "SELECT * from stocks where id = 1"
    r = request.Request (DB_SQLITE3, dbpath, None, None, None, (statement,), callback = callback1)
    f.execute (r)
    
    statement = 1
    r = request.Request (DB_SQLITE3, dbpath, None, None, None, (statement,), callback = callback5)
    f.execute (r)
    
def test_alchenmy (dbpath, log):
    f = synsqlite3.SynConnect (dbpath, logger = log.get ("app"))
    
    statement = stocks.select().where(stocks.c.id == 1)
    r = request.Request (DB_SQLITE3, dbpath, None, None, None, (statement,), callback = callback1)
    f.execute (r)
    
    statement = stocks.insert().values (id = 2, date = '2019-1-30', trans = "SELL", symbol = "APL", qty = 200, price = 1600.0)
    r = request.Request (DB_SQLITE3, dbpath, None, None, None, (statement,), callback = callback2)
    f.execute (r)
    
    statement = stocks.select().where(stocks.c.id >= 1)
    r = request.Request (DB_SQLITE3, dbpath, None, None, None, (statement,), callback = callback3)
    f.execute (r)
    
    statement = stocks.update().values(symbol='BIX').where(stocks.c.id == 2)
    r = request.Request (DB_SQLITE3, dbpath, None, None, None, (statement,), callback = callback2)
    f.execute (r)
    
    statement = stocks.select().where(stocks.c.id == 2)
    r = request.Request (DB_SQLITE3, dbpath, None, None, None, (statement,), callback = callback4)
    f.execute (r)    
        
    statement = stocks.delete().where(stocks.c.id == 2)
    r = request.Request (DB_SQLITE3, dbpath, None, None, None, (statement,), callback = callback2)
    f.execute (r)
    
    statement = stocks.select().where(stocks.c.id > 1)
    r = request.Request (DB_SQLITE3, dbpath, None, None, None, (statement,), callback = callback2)
    f.execute (r)
    
def test_asynpsycopg2 (dbpath, log):
    f = asynpsycopg2.AsynConnect (("127.0.0.1", 5432), logger = log.get ("app"))
    
    statement = stocks.select().where(stocks.c.id == 1)
    r = request.Request (DB_PGSQL, None, None, None, None, (statement,))
    f.begin_tran (r)
    assert f.out_buffer == """SELECT stocks.id, stocks.date, stocks.trans, stocks.symbol, stocks.qty, stocks.price 
FROM stocks 
WHERE stocks.id = 1"""
    
    statement = stocks.insert().values (id = 2, date = '2019-1-30', trans = "SELL", symbol = "APL", qty = 200, price = 1600.0)
    r = request.Request (DB_PGSQL, dbpath, None, None, None, (statement,), callback = callback2)
    f.begin_tran (r)
    assert f.out_buffer == "INSERT INTO stocks (id, date, trans, symbol, qty, price) VALUES (2, '2019-1-30', 'SELL', 'APL', 200, 1600.0)"
    
    statement = stocks.delete().where(stocks.c.id == 2)
    r = request.Request (DB_PGSQL, dbpath, None, None, None, (statement,), callback = callback2)
    f.begin_tran (r)
    assert f.out_buffer == "DELETE FROM stocks WHERE stocks.id = 2"
    
    statement = stocks.update().values(symbol='BIX').where(stocks.c.id == 2)
    r = request.Request (DB_PGSQL, dbpath, None, None, None, (statement,), callback = callback2)
    f.begin_tran (r)
    assert f.out_buffer == "UPDATE stocks SET symbol='BIX' WHERE stocks.id = 2"
    
    statement = 1
    r = request.Request (DB_PGSQL, dbpath, None, None, None, (statement,), callback = callback2)
    f.begin_tran (r)
    assert f.out_buffer == ""
    assert f.exception_class is AttributeError
    
    