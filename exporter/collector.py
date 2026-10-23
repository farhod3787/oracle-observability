import time
import logging
from typing import Iterable, List
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
from prometheus_client.registry import Collector

from exporter.db import OracleDB
from exporter.config import Config
from exporter import queries

logger = logging.getLogger("oracle_exporter.collector")

class OracleCollector(Collector):
    def __init__(self, db: OracleDB, config: Config):
        self.db = db
        self.config = config
        self._last_scrape_time = 0.0
        self._cached_metrics: List[Any] = []

    def collect(self) -> Iterable:
        now = time.time()
        # Serve from cache if within TTL
        if (now - self._last_scrape_time) < self.config.cache_ttl_seconds and self._cached_metrics:
            logger.debug("Serving metrics from cache (age: %.2fs)", now - self._last_scrape_time)
            for metric in self._cached_metrics:
                yield metric
            return

        start_time = time.time()
        metrics = []

        up_metric = GaugeMetricFamily("oracle_up", "Oracle database reachability (1 = reachable, 0 = unreachable)")
        scrape_duration_metric = GaugeMetricFamily(
            "oracle_scrape_duration_seconds", "Total time spent collecting metrics from Oracle DB"
        )

        try:
            # 1. Instance and DB Information
            instance_info_metric = GaugeMetricFamily(
                "oracle_instance_info",
                "Oracle instance information and metadata",
                labels=["instance_name", "host_name", "version", "status", "database_status"]
            )
            uptime_metric = GaugeMetricFamily(
                "oracle_instance_uptime_seconds", "Oracle instance uptime in seconds", labels=["instance_name"]
            )

            instances = self.db.execute_query(queries.QUERY_INSTANCE)
            primary_instance = "UNKNOWN"
            if instances:
                inst = instances[0]
                primary_instance = str(inst.get("instance_name", "UNKNOWN"))
                instance_info_metric.add_metric(
                    [
                        primary_instance,
                        str(inst.get("host_name", "")),
                        str(inst.get("version", "")),
                        str(inst.get("status", "")),
                        str(inst.get("database_status", "")),
                    ],
                    1.0
                )
                uptime_metric.add_metric([primary_instance], float(inst.get("uptime_seconds", 0)))
                metrics.extend([instance_info_metric, uptime_metric])

            # Database Role / Mode
            try:
                db_rows = self.db.execute_query(queries.QUERY_DATABASE)
                if db_rows:
                    db_info_metric = GaugeMetricFamily(
                        "oracle_database_info",
                        "Oracle database open mode and role",
                        labels=["name", "open_mode", "database_role"]
                    )
                    db_info = db_rows[0]
                    db_info_metric.add_metric(
                        [
                            str(db_info.get("name", "")),
                            str(db_info.get("open_mode", "")),
                            str(db_info.get("database_role", "")),
                        ],
                        1.0
                    )
                    metrics.append(db_info_metric)
            except Exception as e:
                logger.warning("Failed to collect database info: %s", e)

            # 2. Tablespace Usage
            try:
                ts_rows = self.db.execute_query(queries.QUERY_TABLESPACES)
                ts_used_bytes = GaugeMetricFamily(
                    "oracle_tablespace_used_bytes",
                    "Used tablespace size in bytes",
                    labels=["tablespace_name", "tablespace_type"]
                )
                ts_max_bytes = GaugeMetricFamily(
                    "oracle_tablespace_max_bytes",
                    "Maximum tablespace size in bytes (including autoextend)",
                    labels=["tablespace_name", "tablespace_type"]
                )
                ts_used_pct = GaugeMetricFamily(
                    "oracle_tablespace_used_percent",
                    "Percentage of tablespace space utilized",
                    labels=["tablespace_name", "tablespace_type"]
                )

                for row in ts_rows:
                    ts_name = str(row.get("tablespace_name", "UNKNOWN"))
                    ts_type = str(row.get("tablespace_type", "PERMANENT"))
                    used_b = float(row.get("used_bytes") or 0)
                    max_b = float(row.get("max_bytes") or 0)
                    pct = float(row.get("used_percent") or 0)

                    ts_used_bytes.add_metric([ts_name, ts_type], used_b)
                    ts_max_bytes.add_metric([ts_name, ts_type], max_b)
                    ts_used_pct.add_metric([ts_name, ts_type], pct)

                metrics.extend([ts_used_bytes, ts_max_bytes, ts_used_pct])
            except Exception as e:
                logger.warning("Failed to collect tablespace metrics: %s", e)

            # 3. Sessions Breakdown & Limits
            try:
                sess_rows = self.db.execute_query(queries.QUERY_SESSIONS)
                sess_total_metric = GaugeMetricFamily(
                    "oracle_sessions_total",
                    "Number of Oracle database sessions",
                    labels=["status", "session_type"]
                )
                total_active_users = 0
                total_sessions = 0
                for row in sess_rows:
                    status = str(row.get("status", "UNKNOWN"))
                    stype = str(row.get("session_type", "USER"))
                    count = float(row.get("session_count") or 0)
                    total_sessions += count
                    if status == "ACTIVE" and stype == "USER":
                        total_active_users += count
                    sess_total_metric.add_metric([status, stype], count)

                metrics.append(sess_total_metric)

                # Limit
                limit_rows = self.db.execute_query(queries.QUERY_SESSION_LIMIT)
                if limit_rows:
                    max_sessions = float(limit_rows[0].get("max_sessions") or 0)
                    sess_limit_metric = GaugeMetricFamily(
                        "oracle_sessions_limit", "Maximum session limit configured in parameters"
                    )
                    sess_limit_metric.add_metric([], max_sessions)
                    metrics.append(sess_limit_metric)

                    if max_sessions > 0:
                        sess_pct_metric = GaugeMetricFamily(
                            "oracle_sessions_usage_percent",
                            "Current session count as percentage of configured parameter limit"
                        )
                        sess_pct_metric.add_metric([], round((total_sessions / max_sessions) * 100, 2))
                        metrics.append(sess_pct_metric)
            except Exception as e:
                logger.warning("Failed to collect session metrics: %s", e)

            # 4. Blocking Sessions / Lock Contention
            try:
                block_rows = self.db.execute_query(queries.QUERY_BLOCKING_SESSIONS)
                if block_rows:
                    blocking_count = float(block_rows[0].get("blocking_count") or 0)
                    block_metric = GaugeMetricFamily(
                        "oracle_blocking_sessions_count",
                        "Count of distinct sessions actively blocking other sessions"
                    )
                    block_metric.add_metric([], blocking_count)
                    metrics.append(block_metric)
            except Exception as e:
                logger.warning("Failed to collect blocking sessions metrics: %s", e)

            # 5. Memory (SGA & PGA)
            try:
                sga_rows = self.db.execute_query(queries.QUERY_SGA)
                sga_metric = GaugeMetricFamily(
                    "oracle_sga_bytes", "Oracle System Global Area component sizes in bytes", labels=["pool"]
                )
                for row in sga_rows:
                    name = str(row.get("name", "Unknown"))
                    val = float(row.get("bytes") or 0)
                    sga_metric.add_metric([name], val)
                metrics.append(sga_metric)
            except Exception as e:
                logger.warning("Failed to collect SGA metrics: %s", e)

            try:
                pga_rows = self.db.execute_query(queries.QUERY_PGA)
                pga_metric = GaugeMetricFamily(
                    "oracle_pga_bytes", "Oracle Program Global Area statistics in bytes", labels=["stat"]
                )
                pga_hit_metric = GaugeMetricFamily(
                    "oracle_pga_cache_hit_percent", "Oracle PGA Cache Hit Percentage"
                )
                for row in pga_rows:
                    name = str(row.get("name", "")).strip()
                    val = float(row.get("value") or 0)
                    if name == "cache hit percentage":
                        pga_hit_metric.add_metric([], val)
                    else:
                        clean_name = name.replace(" ", "_").lower()
                        pga_metric.add_metric([clean_name], val)

                metrics.append(pga_metric)
                metrics.append(pga_hit_metric)
            except Exception as e:
                logger.warning("Failed to collect PGA metrics: %s", e)

            # 6. Wait Classes
            try:
                wait_rows = self.db.execute_query(queries.QUERY_WAIT_CLASSES)
                wait_waits_metric = CounterMetricFamily(
                    "oracle_wait_class_waits_total",
                    "Total wait events count per wait class",
                    labels=["wait_class"]
                )
                wait_time_metric = CounterMetricFamily(
                    "oracle_wait_class_time_seconds_total",
                    "Total time waited in seconds per wait class",
                    labels=["wait_class"]
                )
                for row in wait_rows:
                    w_class = str(row.get("wait_class", "Other"))
                    waits = float(row.get("total_waits") or 0)
                    time_sec = float(row.get("time_waited_seconds") or 0)
                    wait_waits_metric.add_metric([w_class], waits)
                    wait_time_metric.add_metric([w_class], time_sec)

                metrics.extend([wait_waits_metric, wait_time_metric])
            except Exception as e:
                logger.warning("Failed to collect wait class metrics: %s", e)

            # 7. System Activity Counters (v$sysstat)
            try:
                stat_rows = self.db.execute_query(queries.QUERY_SYSSTAT)
                sysstat_metric = CounterMetricFamily(
                    "oracle_sysstat_total",
                    "Oracle system statistics counters",
                    labels=["statistic"]
                )
                for row in stat_rows:
                    stat_name = str(row.get("name", "")).replace(" ", "_").replace("(", "").replace(")", "").lower()
                    val = float(row.get("value") or 0)
                    sysstat_metric.add_metric([stat_name], val)

                metrics.append(sysstat_metric)
            except Exception as e:
                logger.warning("Failed to collect sysstat metrics: %s", e)

            up_metric.add_metric([], 1.0)

        except Exception as e:
            logger.error("Error scraping Oracle metrics: %s", e, exc_info=True)
            up_metric.add_metric([], 0.0)

        duration = time.time() - start_time
        scrape_duration_metric.add_metric([], duration)
        metrics.extend([up_metric, scrape_duration_metric])

        # Cache results
        self._cached_metrics = metrics
        self._last_scrape_time = time.time()

        for metric in metrics:
            yield metric
