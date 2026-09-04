import psycopg2, subprocess, os

psql_exe = r'C:\Program Files\PostgreSQL\17\bin\psql.exe'
pg_password = 'postgres'

print("=== Testing postgres superuser connection ===")
try:
    conn = psycopg2.connect(
        host='localhost', port=5432, dbname='postgres',
        user='postgres', password=pg_password
    )
    cur = conn.cursor()
    cur.execute("SELECT current_user, version();")
    row = cur.fetchone()
    print(f"SUCCESS: connected as {row[0]}")
    print(f"PostgreSQL version: {row[1][:60]}")

    # List databases
    cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;")
    dbs = [r[0] for r in cur.fetchall()]
    print(f"Available databases: {dbs}")

    # Check if pod_db exists
    cur.execute("SELECT datname FROM pg_database WHERE datname = 'pod_db';")
    pod_db = cur.fetchone()
    print(f"pod_db exists: {pod_db is not None}")

    # Check if pod_user exists
    cur.execute("SELECT usename FROM pg_user WHERE usename = 'pod_user';")
    pod_user = cur.fetchone()
    print(f"pod_user exists: {pod_user is not None}")

    conn.close()
except Exception as e:
    print(f"FAILED: {e}")
