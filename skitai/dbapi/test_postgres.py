import psycopg2

conn = psycopg2.connect (
	dbname = "mydb",
	user = "postgres",
	password = "!kms2000",
	host = "mydb.c25zyujwtzky.us-east-1.rds.amazonaws.com"	
	)
	
cur = conn.cursor()
cur.execute ("SELECT city, temp_lo, temp_hi, prcp, date FROM weather;")

print cur.fetchall ()



	