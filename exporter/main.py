import sys
import time
import signal
import logging
from prometheus_client import start_http_server, REGISTRY

from exporter.config import config
from exporter.db import OracleDB
from exporter.collector import OracleCollector

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def main():
    setup_logging()
    logger = logging.getLogger("oracle_exporter")
    logger.info("Initializing Oracle Observability Exporter...")
    logger.info("Target Oracle DSN: %s (User: %s)", config.dsn, config.oracle_user)

    db = OracleDB(config)
    collector = OracleCollector(db, config)
    REGISTRY.register(collector)

    # Graceful shutdown handler
    def shutdown_handler(signum, frame):
        logger.info("Received termination signal (%d). Shutting down...", signum)
        db.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        start_http_server(config.exporter_port, addr=config.exporter_host)
        logger.info(
            "Oracle Prometheus Exporter listening on http://%s:%d/metrics",
            config.exporter_host,
            config.exporter_port
        )
    except Exception as e:
        logger.critical("Failed to start exporter HTTP server: %s", e)
        sys.exit(1)

    # Keep running
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
