"""SQL queries for Oracle Database Observability."""

# Instance and Database Health
QUERY_INSTANCE = """
SELECT 
    instance_name, 
    host_name, 
    version, 
    status, 
    database_status, 
    archiver,
    ROUND((SYSDATE - startup_time) * 86400) AS uptime_seconds
FROM v$instance
"""

QUERY_DATABASE = """
SELECT name, open_mode, database_role FROM v$database
"""

# Tablespace Utilization (Calculates allocated, used, and autoextend capacity)
QUERY_TABLESPACES = """
SELECT 
    m.tablespace_name,
    NVL(t.contents, 'PERMANENT') AS tablespace_type,
    ROUND(m.used_space * t.block_size) AS used_bytes,
    ROUND(m.tablespace_size * t.block_size) AS max_bytes,
    ROUND(m.used_percent, 2) AS used_percent
FROM dba_tablespace_usage_metrics m
JOIN dba_tablespaces t ON m.tablespace_name = t.tablespace_name
"""

# Session Breakdown (Active, Inactive, Background)
QUERY_SESSIONS = """
SELECT 
    NVL(status, 'UNKNOWN') AS status, 
    NVL(type, 'USER') AS session_type, 
    COUNT(*) AS session_count
FROM v$session
GROUP BY status, type
"""

QUERY_SESSION_LIMIT = """
SELECT TO_NUMBER(value) AS max_sessions FROM v$parameter WHERE name = 'sessions'
"""

QUERY_BLOCKING_SESSIONS = """
SELECT COUNT(DISTINCT blocking_session) AS blocking_count
FROM v$session
WHERE blocking_session IS NOT NULL
"""

# Memory (SGA and PGA)
QUERY_SGA = """
SELECT name, bytes 
FROM v$sgainfo 
WHERE bytes > 0
"""

QUERY_PGA = """
SELECT name, value 
FROM v$pgastat 
WHERE name IN (
    'total PGA allocated', 
    'total PGA inuse', 
    'maximum PGA allocated', 
    'PGA memory freed to OS', 
    'cache hit percentage'
)
"""

# Wait Events by Wait Class (non-idle)
QUERY_WAIT_CLASSES = """
SELECT 
    wait_class, 
    total_waits, 
    ROUND(time_waited_micro / 1000000, 4) AS time_waited_seconds
FROM v$system_wait_class
WHERE wait_class != 'Idle'
"""

# System Activity & Workload Counters
QUERY_SYSSTAT = """
SELECT name, value 
FROM v$sysstat 
WHERE name IN (
    'user commits',
    'user rollbacks',
    'execute count',
    'parse count (total)',
    'parse count (hard)',
    'physical reads',
    'physical writes',
    'redo size',
    'session logical reads'
)
"""
