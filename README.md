# 🛰️ Oracle Database Observability Stack

A production-ready observability and monitoring stack for **Oracle Database** (11g, 12c, 19c, 21c, and 23ai) using **Prometheus**, **Grafana**, and a lightweight **Python Prometheus Exporter** running in **Thin Mode** (zero Oracle Client dependencies).

---

## 🏗️ Architecture

```
                                    +------------------------------------------+
                                    |          Oracle Database Host            |
                                    |   (V$ / DBA Performance & Health Views)  |
                                    +--------------------+---------------------+
                                                         |
                                                         | SQL (Thin Mode, Port 1521)
                                                         v
                                    +--------------------+---------------------+
                                    |      oracle-exporter (:9161)             |
                                    |  - Python + python-oracledb              |
                                    |  - Built-in TTL Cache & Health Checks    |
                                    +--------------------+---------------------+
                                                         |
                                                         | Scrape /metrics (15s)
                                                         v
                                    +--------------------+---------------------+
                                    |         Prometheus (:9090)               |
                                    |  - TSDB Metric Storage                   |
                                    |  - Evaluates Alerting Rules              |
                                    +--------------------+---------------------+
                                                         |
                                                         | Queries PromQL
                                                         v
                                    +--------------------+---------------------+
                                    |          Grafana (:3000)                 |
                                    |  - Pre-provisioned Datasources           |
                                    |  - Pre-built Health & Storage Dashboard  |
                                    +------------------------------------------+
```

---

## 📊 Metrics Collected

| Metric Family | Type | Description |
| :--- | :--- | :--- |
| `oracle_up` | Gauge | Reachability of the database (1 = UP, 0 = DOWN) |
| `oracle_instance_info` | Gauge | Hostname, version, instance name, and database status |
| `oracle_instance_uptime_seconds` | Gauge | Instance uptime in seconds |
| `oracle_tablespace_used_bytes` | Gauge | Tablespace used bytes |
| `oracle_tablespace_max_bytes` | Gauge | Total tablespace capacity (accounting for autoextension) |
| `oracle_tablespace_used_percent` | Gauge | Percentage of tablespace consumed |
| `oracle_sessions_total` | Gauge | Active/Inactive sessions grouped by USER/BACKGROUND |
| `oracle_sessions_limit` | Gauge | Parameter limit configured for max concurrent sessions |
| `oracle_sessions_usage_percent`| Gauge | Session count relative to parameter limit |
| `oracle_blocking_sessions_count`| Gauge | Number of sessions actively blocking other sessions |
| `oracle_sga_bytes` | Gauge | Memory allocation across SGA pools (Buffer cache, Shared pool, etc.) |
| `oracle_pga_bytes` | Gauge | Total allocated and in-use PGA memory |
| `oracle_pga_cache_hit_percent` | Gauge | PGA workarea execution efficiency |
| `oracle_wait_class_waits_total`| Counter | Total waits per wait class (User I/O, Concurrency, etc.) |
| `oracle_wait_class_time_seconds_total` | Counter | Cumulative wait time per wait class |
| `oracle_sysstat_total` | Counter | Commits, rollbacks, physical reads, and logical reads |

---

## 📁 Project Structure

```
oracle-observability/
├── docker-compose.yml              # Complete 1-click Prometheus + Grafana + Exporter stack
├── Dockerfile                      # Exporter container build
├── requirements.txt                # Python dependencies (python-oracledb, prometheus-client)
├── .env.example                    # Environment configuration template
├── .env                            # Active environment settings
├── exporter/
│   ├── main.py                     # Exporter entry point & Prometheus HTTP server
│   ├── config.py                   # Environment loader & configuration dataclass
│   ├── db.py                       # Resilient Oracle connection pool (Thin Mode)
│   ├── collector.py                # Custom Prometheus Collector with TTL caching
│   └── queries.py                  # Optimized Oracle V$ and DBA SQL queries
├── prometheus/
│   ├── prometheus.yml              # Prometheus scrape configuration
│   └── rules/
│       └── oracle_alerts.yml       # Production alert rules (DB Down, Tablespace Full, etc.)
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/            # Automatic Prometheus datasource config
│   │   └── dashboards/             # Automatic dashboard provisioning
│   └── dashboards/
│       └── oracle_overview.json    # Complete Oracle Observability Dashboard
└── scripts/
    ├── oracle_grant_permissions.sql # SQL script to create monitoring user & grants
    └── test_connection.py          # Quick CLI test tool to verify DB connectivity
```

---

## 🚀 Quickstart Guide

### Step 1: Create the Monitoring User in Oracle

Execute [scripts/oracle_grant_permissions.sql](file:///C:/Users/Farhod/.gemini/antigravity/scratch/oracle-observability/scripts/oracle_grant_permissions.sql) using `sqlplus` or Oracle SQL Developer as `SYSDBA`:

```bash
sqlplus sys/YourSysPassword@localhost:1521/ORCLPDB1 as sysdba @scripts/oracle_grant_permissions.sql
```

> **Note for Multitenant (CDB/PDB):**
> If you are monitoring the entire CDB from the root container, create a common user `c##monitor_user`. If you are monitoring a specific Pluggable Database (PDB, recommended), run the script inside that PDB.

---

### Step 2: Configure `.env`

Edit `.env` with your Oracle connection credentials:

```ini
ORACLE_USER=monitor_user
ORACLE_PASSWORD=MonitoringPassword#2026
ORACLE_HOST=host.docker.internal   # Or your Oracle IP/hostname
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=ORCLPDB1       # Or ORACLE_SID=ORCL
ORACLE_CONNECTION_MODE=THIN
```

---

### Step 3: Test Connectivity

Before running the full stack, run the diagnostic test script:

```bash
# Optional: install requirements in a virtual environment
python -m venv .venv
.venv\Scripts\activate       # On Windows (or source .venv/bin/activate on Linux)
pip install -r requirements.txt

# Run connection diagnostic
python scripts/test_connection.py
```

---

### Step 4: Start the Stack with Docker Compose

```bash
docker compose up -d --build
```

Access the interfaces:
- **Grafana Dashboard**: [http://localhost:3000](http://localhost:3000) (Login: `admin` / `admin`)
- **Prometheus UI**: [http://localhost:9090](http://localhost:9090)
- **Prometheus Metrics**: [http://localhost:9161/metrics](http://localhost:9161/metrics)

The Grafana dashboard **"Oracle Database Observability"** is automatically provisioned and set as the default homepage.

---

### Step 5: (Alternative) Run Standalone without Docker

If you want to run the exporter directly on the host machine:

```bash
python -m exporter.main
```

The metrics will be accessible immediately at `http://localhost:9161/metrics`.

---

## 🔔 Configured Alerts

The Prometheus rules in [prometheus/rules/oracle_alerts.yml](file:///C:/Users/Farhod/.gemini/antigravity/scratch/oracle-observability/prometheus/rules/oracle_alerts.yml) automatically monitor:
- **`OracleDatabaseDown`**: Fires when Oracle is unreachable for > 1 minute (Critical).
- **`OracleTablespaceCritical`**: Fires when tablespace utilization exceeds 90% (Critical).
- **`OracleTablespaceWarning`**: Fires when tablespace utilization exceeds 80% (Warning).
- **`OracleHighSessionUsage`**: Fires when session count exceeds 85% of parameter limit (Warning).
- **`OracleBlockingSessionsDetected`**: Fires when blocking locks persist for > 2 minutes (Warning).
- **`OraclePgaCacheHitLow`**: Fires when PGA cache hit percentage falls below 75% (Warning).
