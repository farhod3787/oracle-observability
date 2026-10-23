import logging
import oracledb
from typing import Any, List, Dict
from exporter.config import Config

logger = logging.getLogger("oracle_exporter.db")

class OracleDB:
    def __init__(self, config: Config):
        self.config = config
        self._pool: oracledb.ConnectionPool | None = None
        self._init_client_mode()

    def _init_client_mode(self):
        # python-oracledb is thin mode by default.
        # Thick mode is only initialized if explicitly requested and instant client is available.
        if self.config.connection_mode == "THICK":
            try:
                oracledb.init_oracle_client()
                logger.info("Oracle Client initialized in THICK mode.")
            except Exception as e:
                logger.warning("Failed to initialize THICK mode (%s). Falling back to THIN mode.", e)
        else:
            logger.info("Using python-oracledb in THIN mode (no local Oracle client required).")

    def get_pool(self) -> oracledb.ConnectionPool:
        if self._pool is None:
            logger.info("Connecting to Oracle DSN: %s with user: %s", self.config.dsn, self.config.oracle_user)
            self._pool = oracledb.create_pool(
                user=self.config.oracle_user,
                password=self.config.oracle_password,
                dsn=self.config.dsn,
                min=1,
                max=4,
                increment=1,
                tcp_connect_timeout=self.config.connect_timeout,
                retry_count=1,
                retry_delay=1
            )
            logger.info("Oracle connection pool initialized successfully.")
        return self._pool

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a query and returns results as a list of lower-case key dictionaries."""
        pool = self.get_pool()
        with pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.call_timeout = self.config.query_timeout * 1000  # ms
                cursor.execute(query)
                columns = [col[0].lower() for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]

    def check_connection(self) -> Dict[str, Any]:
        """Simple ping/test query returning db status and version."""
        rows = self.execute_query("SELECT 1 AS alive, SYSDATE AS current_db_time FROM dual")
        return rows[0] if rows else {}

    def close(self):
        if self._pool:
            try:
                self._pool.close()
                logger.info("Oracle connection pool closed.")
            except Exception as e:
                logger.error("Error closing Oracle connection pool: %s", e)
            self._pool = None
