import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    oracle_user: str = os.getenv("ORACLE_USER", "monitor_user")
    oracle_password: str = os.getenv("ORACLE_PASSWORD", "")
    oracle_host: str = os.getenv("ORACLE_HOST", "localhost")
    oracle_port: int = int(os.getenv("ORACLE_PORT", "1521"))
    oracle_service_name: str | None = os.getenv("ORACLE_SERVICE_NAME", None)
    oracle_sid: str | None = os.getenv("ORACLE_SID", None)
    connection_mode: str = os.getenv("ORACLE_CONNECTION_MODE", "THIN").upper()
    connect_timeout: int = int(os.getenv("ORACLE_CONNECT_TIMEOUT", "5"))
    query_timeout: int = int(os.getenv("ORACLE_QUERY_TIMEOUT", "10"))

    exporter_host: str = os.getenv("EXPORTER_HOST", "0.0.0.0")
    exporter_port: int = int(os.getenv("EXPORTER_PORT", "9161"))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "10"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    @property
    def dsn(self) -> str:
        if self.oracle_service_name:
            return f"{self.oracle_host}:{self.oracle_port}/{self.oracle_service_name}"
        elif self.oracle_sid:
            return f"{self.oracle_host}:{self.oracle_port}:{self.oracle_sid}"
        else:
            return f"{self.oracle_host}:{self.oracle_port}/ORCLPDB1"

config = Config()
