"""Quick diagnostic test script for Oracle database connectivity."""

import sys
import time
from exporter.config import config
from exporter.db import OracleDB
from exporter import queries

def main():
    print("=" * 60)
    print(" Oracle Database Observability - Connection Diagnostic Tool")
    print("=" * 60)
    print(f"Target Host    : {config.oracle_host}:{config.oracle_port}")
    print(f"Service / SID  : {config.oracle_service_name or config.oracle_sid}")
    print(f"Full DSN       : {config.dsn}")
    print(f"Username       : {config.oracle_user}")
    print(f"Mode           : {config.connection_mode}")
    print("-" * 60)

    start = time.time()
    try:
        db = OracleDB(config)
        print("[+] Connecting to Oracle...")
        alive_info = db.check_connection()
        latency_ms = (time.time() - start) * 1000
        print(f"[✓] Successfully connected to Oracle! Latency: {latency_ms:.2f} ms")
        print(f"    DB Time: {alive_info.get('current_db_time')}")

        print("\n[+] Checking Instance details...")
        inst = db.execute_query(queries.QUERY_INSTANCE)
        if inst:
            print(f"    Instance Name  : {inst[0].get('instance_name')}")
            print(f"    Version        : {inst[0].get('version')}")
            print(f"    Status         : {inst[0].get('status')}")
            print(f"    Uptime Seconds : {inst[0].get('uptime_seconds')}")
        else:
            print("    [!] Warning: v$instance query returned no rows.")

        print("\n[+] Checking Tablespace access...")
        tablespaces = db.execute_query(queries.QUERY_TABLESPACES)
        print(f"    Found {len(tablespaces)} tablespaces:")
        for ts in tablespaces[:5]:
            print(f"      - {ts.get('tablespace_name')}: {ts.get('used_percent')}% used ({ts.get('used_bytes')} / {ts.get('max_bytes')} bytes)")
        if len(tablespaces) > 5:
            print(f"      ... and {len(tablespaces) - 5} more.")

        print("\n[+] Checking Session privileges...")
        sessions = db.execute_query(queries.QUERY_SESSIONS)
        print(f"    Session summary rows: {len(sessions)}")

        print("\n" + "=" * 60)
        print(" SUCCESS: All necessary queries and permissions verified!")
        print(" You can now launch the exporter with: python -m exporter.main")
        print(" or start the full stack with: docker compose up -d")
        print("=" * 60)
        db.close()

    except Exception as e:
        print("\n" + "!" * 60)
        print(f"[ERROR] Connection or Query failed: {e}")
        print("!" * 60)
        print("\nTroubleshooting tips:")
        print(" 1. Check if the Oracle listener is running on the target port.")
        print(" 2. Confirm user and password in .env match scripts/oracle_grant_permissions.sql.")
        print(" 3. Verify user has SELECT_CATALOG_ROLE or explicit view grants.")
        print(" 4. If running in multitenant (CDB/PDB), ensure you connect to the intended PDB service name.")
        sys.exit(1)

if __name__ == "__main__":
    main()
