-- =====================================================================
-- Oracle Database Observability - Monitoring User Setup
-- Run this script as SYSDBA or an ADMIN user.
-- =====================================================================

-- 1. Create dedicated monitoring user
-- Note: In Oracle Multitenant (CDB/PDB), if creating in CDB root, prefix with C##
-- e.g., CREATE USER c##monitor_user IDENTIFIED BY "SecurePassword123#";
-- If creating inside a PDB (recommended for PDB observability):
CREATE USER monitor_user IDENTIFIED BY "MonitoringPassword#2026"
  DEFAULT TABLESPACE users
  TEMPORARY TABLESPACE temp
  ACCOUNT UNLOCK;

-- 2. Basic connection privilege
GRANT CREATE SESSION TO monitor_user;

-- 3. Dictionary and Catalog role (Recommended for observability)
-- SELECT_CATALOG_ROLE provides read access to data dictionary views (DBA_*, V_$)
GRANT SELECT_CATALOG_ROLE TO monitor_user;

-- 4. Specific V$ and DBA views required if SELECT_CATALOG_ROLE is not desired
-- (Least privilege alternative to SELECT_CATALOG_ROLE)
GRANT SELECT ON sys.v_$instance TO monitor_user;
GRANT SELECT ON sys.v_$database TO monitor_user;
GRANT SELECT ON sys.v_$session TO monitor_user;
GRANT SELECT ON sys.v_$parameter TO monitor_user;
GRANT SELECT ON sys.v_$sgainfo TO monitor_user;
GRANT SELECT ON sys.v_$pgastat TO monitor_user;
GRANT SELECT ON sys.v_$system_wait_class TO monitor_user;
GRANT SELECT ON sys.v_$sysstat TO monitor_user;
GRANT SELECT ON sys.v_$tablespace TO monitor_user;
GRANT SELECT ON sys.dba_tablespaces TO monitor_user;
GRANT SELECT ON sys.dba_tablespace_usage_metrics TO monitor_user;
GRANT SELECT ON sys.dba_data_files TO monitor_user;
GRANT SELECT ON sys.dba_free_space TO monitor_user;

-- Verify user creation
SELECT username, account_status, default_tablespace 
FROM dba_users 
WHERE username = 'MONITOR_USER';
