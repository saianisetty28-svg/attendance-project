import os
import psycopg2

DB_SETTINGS = {
    "database": os.getenv("PSQL_DATABASE", "goldeneyelocal"),
    "user": os.getenv("PSQL_USER", "goldeneye"),
    "password": os.getenv("PSQL_PASSWORD", "FPGlV4L$S92Rdk*"),
    "host": os.getenv("PSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("PSQL_PORT", "5433")),
}

def get_conn():
    return psycopg2.connect(**DB_SETTINGS)

if __name__ == "__main__":
    conn = None
    try:
        print("Attempting PostgreSQL connection via SSH tunnel...")
        # Get the connection
        conn = get_conn()
        
        # The 'with' block here still safely handles the cursor
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            print("\n✅ Connection Successful! Database version:")
            print(cursor.fetchone())
            
    except Exception as exc:
        print(f"\n❌ Connection or query failed: {exc}")
        
    finally:
        # This guarantees the connection is closed, even if the code crashes!
        if conn is not None:
            conn.close()
            print("Database connection safely closed.")