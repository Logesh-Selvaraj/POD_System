import os, subprocess

# Find psql.exe
pg_base = r"C:\Program Files\PostgreSQL"
psql_paths = []
if os.path.exists(pg_base):
    print(f"PostgreSQL installed at: {pg_base}")
    for version_dir in os.listdir(pg_base):
        bin_dir = os.path.join(pg_base, version_dir, "bin")
        psql = os.path.join(bin_dir, "psql.exe")
        if os.path.exists(psql):
            psql_paths.append(psql)
            print(f"  Found psql.exe: {psql}")
else:
    print("PostgreSQL NOT found at C:\\Program Files\\PostgreSQL")

if not psql_paths:
    print("No psql.exe found in standard locations")
else:
    psql_exe = psql_paths[0]
    # Try to connect as postgres superuser with various passwords
    passwords = ["postgres", "admin", "password", "123456", ""]
    for pw in passwords:
        env = os.environ.copy()
        env["PGPASSWORD"] = pw
        try:
            result = subprocess.run(
                [psql_exe, "-U", "postgres", "-h", "localhost", "-p", "5432", "-c", r"\l"],
                env=env, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print(f"\nSUCCESS as postgres with password='{pw}'")
                print(result.stdout[:500])
                break
            else:
                print(f"FAILED  postgres / '{pw}': {result.stderr.strip()[:80]}")
        except Exception as e:
            print(f"ERROR: {e}")
