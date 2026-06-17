import psycopg2

def get_conn():
    return psycopg2.connect(
        host="localhost",
        database="attendance_db",
        user="postgres",
        password="password"
    )