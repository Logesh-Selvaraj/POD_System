import psycopg2

configs = [
    {"host": "localhost", "port": 5432, "dbname": "pod_db", "user": "pod_user", "password": "pod_password"},
    {"host": "localhost", "port": 5432, "dbname": "pod_db", "user": "postgres", "password": "postgres"},
    {"host": "localhost", "port": 5432, "dbname": "pod_db", "user": "postgres", "password": ""},
    {"host": "localhost", "port": 5432, "dbname": "postgres", "user": "pod_user", "password": "pod_password"},
]

print("=== PostgreSQL Connection Tests ===")
for cfg in configs:
    try:
        conn = psycopg2.connect(**cfg)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        ver = cur.fetchone()[0][:60]
        print(f"SUCCESS  user={cfg['user']}  db={cfg['dbname']}  -> {ver}")
        # List databases
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;")
        dbs = [row[0] for row in cur.fetchall()]
        print(f"         Available databases: {dbs}")
        # Check if pod_db exists
        cur.execute("SELECT datname FROM pg_database WHERE datname = 'pod_db';")
        pod_db = cur.fetchone()
        print(f"         pod_db exists: {pod_db is not None}")
        conn.close()
    except Exception as e:
        print(f"FAILED   user={cfg['user']}  db={cfg['dbname']}  -> {str(e)[:100]}")

# Also check pg_hba.conf accessible users via psql
print()
print("=== Checking pod_user existence ===")
try:
    conn = psycopg2.connect(host="localhost", port=5432, dbname="postgres", user="postgres", password="postgres")
    cur = conn.cursor()
    cur.execute("SELECT usename FROM pg_user WHERE usename = 'pod_user';")
    user = cur.fetchone()
    print(f"pod_user exists in pg_user: {user is not None}")
    conn.close()
except Exception as e:
    print(f"Could not check pg_user: {e}")
