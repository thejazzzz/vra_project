import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="vra",
        password="vra",
        database="vra"
    )
    print("Connected! PostgreSQL works.")
    conn.close()

except Exception as e:
    print("Error:", e)
