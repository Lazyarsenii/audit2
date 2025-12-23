"""
Metrics Storage — Datadog-style persistence layer.

Supports multiple storage backends:
- JSON files (development)
- SQLite (local)
- PostgreSQL (production)
- Time-series (future: InfluxDB, TimescaleDB)

Storage structure:
- Metrics (time-series): for trending and historical queries
- Documents: for full analysis reports
- Cache: for fast lookups
"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import sqlite3
from contextlib import contextmanager

from .schema import MetricSet, Metric

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract storage backend."""

    @abstractmethod
    async def save_metrics(self, metrics: MetricSet) -> None:
        """Save a MetricSet."""
        pass

    @abstractmethod
    async def get_metrics(self, analysis_id: str) -> Optional[MetricSet]:
        """Retrieve a MetricSet by analysis ID."""
        pass

    @abstractmethod
    async def list_analyses(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List all analyses (summary only)."""
        pass

    @abstractmethod
    async def query_metrics(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[Metric]:
        """Query metrics by name and filters."""
        pass


class JSONFileStorage(StorageBackend):
    """
    JSON file-based storage for development/testing.

    Structure:
        storage_dir/
        ├── metrics/
        │   ├── {analysis_id}.json
        │   └── ...
        ├── reports/
        │   ├── {analysis_id}_review.md
        │   └── ...
        └── index.json
    """

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.metrics_dir = self.storage_dir / "metrics"
        self.reports_dir = self.storage_dir / "reports"
        self.index_file = self.storage_dir / "index.json"

        # Create directories
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Initialize index
        if not self.index_file.exists():
            self._save_index([])

    def _load_index(self) -> List[Dict[str, Any]]:
        """Load analysis index."""
        if self.index_file.exists():
            return json.loads(self.index_file.read_text())
        return []

    def _save_index(self, index: List[Dict[str, Any]]) -> None:
        """Save analysis index."""
        self.index_file.write_text(json.dumps(index, indent=2))

    async def save_metrics(self, metrics: MetricSet) -> None:
        """Save MetricSet to JSON file."""
        # Save full metrics
        metrics_file = self.metrics_dir / f"{metrics.analysis_id}.json"
        metrics_file.write_text(metrics.to_json())

        # Update index
        index = self._load_index()
        index_entry = {
            "analysis_id": metrics.analysis_id,
            "repo_url": metrics.repo_url,
            "branch": metrics.branch,
            "collected_at": metrics.collected_at.isoformat(),
            "metrics_count": len(metrics.metrics),
        }

        # Update or append
        updated = False
        for i, entry in enumerate(index):
            if entry["analysis_id"] == metrics.analysis_id:
                index[i] = index_entry
                updated = True
                break
        if not updated:
            index.insert(0, index_entry)

        self._save_index(index)
        logger.info(f"Saved metrics for {metrics.analysis_id} ({len(metrics.metrics)} metrics)")

    async def get_metrics(self, analysis_id: str) -> Optional[MetricSet]:
        """Load MetricSet from JSON file."""
        metrics_file = self.metrics_dir / f"{analysis_id}.json"
        if not metrics_file.exists():
            return None

        data = json.loads(metrics_file.read_text())

        # Reconstruct MetricSet
        from .schema import MetricType, MetricSource, MetricCategory, MetricLabel

        metrics_list = []
        for m in data.get("metrics", []):
            metrics_list.append(Metric(
                name=m["name"],
                value=m["value"],
                metric_type=MetricType(m["type"]),
                source=MetricSource(m["source"]),
                category=MetricCategory(m["category"]),
                labels=[MetricLabel(k, v) for k, v in m.get("labels", {}).items()],
                timestamp=datetime.fromisoformat(m["timestamp"]),
                unit=m.get("unit"),
                description=m.get("description"),
            ))

        return MetricSet(
            analysis_id=data["analysis_id"],
            repo_url=data["repo_url"],
            branch=data.get("branch"),
            collected_at=datetime.fromisoformat(data["collected_at"]),
            metrics=metrics_list,
            metadata=data.get("metadata", {}),
        )

    async def list_analyses(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List analyses from index."""
        index = self._load_index()
        return index[offset:offset + limit]

    async def query_metrics(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[Metric]:
        """Query metrics across all analyses."""
        results = []

        for metrics_file in self.metrics_dir.glob("*.json"):
            data = json.loads(metrics_file.read_text())
            collected_at = datetime.fromisoformat(data["collected_at"])

            # Time filter
            if start_time and collected_at < start_time:
                continue
            if end_time and collected_at > end_time:
                continue

            for m in data.get("metrics", []):
                if m["name"] != metric_name:
                    continue

                # Labels filter
                if labels:
                    m_labels = m.get("labels", {})
                    if not all(m_labels.get(k) == v for k, v in labels.items()):
                        continue

                from .schema import MetricType, MetricSource, MetricCategory, MetricLabel
                results.append(Metric(
                    name=m["name"],
                    value=m["value"],
                    metric_type=MetricType(m["type"]),
                    source=MetricSource(m["source"]),
                    category=MetricCategory(m["category"]),
                    labels=[MetricLabel(k, v) for k, v in m.get("labels", {}).items()],
                    timestamp=datetime.fromisoformat(m["timestamp"]),
                ))

        return sorted(results, key=lambda m: m.timestamp, reverse=True)

    async def save_report(self, analysis_id: str, report_type: str, content: str) -> Path:
        """Save a generated report."""
        filename = f"{analysis_id}_{report_type}.md"
        report_file = self.reports_dir / filename
        report_file.write_text(content)
        logger.info(f"Saved report: {report_file}")
        return report_file


class SQLiteStorage(StorageBackend):
    """
    SQLite storage for local production use.

    Tables:
    - analyses: Analysis metadata
    - metrics: Individual metrics (time-series friendly)
    - reports: Generated reports
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._init_db()

    @contextmanager
    def _get_conn(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS analyses (
                    analysis_id TEXT PRIMARY KEY,
                    repo_url TEXT NOT NULL,
                    branch TEXT,
                    collected_at TIMESTAMP NOT NULL,
                    metrics_count INTEGER DEFAULT 0,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value REAL,
                    value_text TEXT,
                    metric_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    labels JSON,
                    unit TEXT,
                    description TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id)
                );

                CREATE INDEX IF NOT EXISTS idx_metrics_analysis ON metrics(analysis_id);
                CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
                CREATE INDEX IF NOT EXISTS idx_metrics_category ON metrics(category);

                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id TEXT NOT NULL,
                    report_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id)
                );
            """)
            conn.commit()

    async def save_metrics(self, metrics: MetricSet) -> None:
        """Save MetricSet to SQLite."""
        with self._get_conn() as conn:
            # Insert/update analysis
            conn.execute("""
                INSERT OR REPLACE INTO analyses
                (analysis_id, repo_url, branch, collected_at, metrics_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                metrics.analysis_id,
                metrics.repo_url,
                metrics.branch,
                metrics.collected_at.isoformat(),
                len(metrics.metrics),
                json.dumps(metrics.metadata),
            ))

            # Delete old metrics for this analysis
            conn.execute("DELETE FROM metrics WHERE analysis_id = ?", (metrics.analysis_id,))

            # Insert metrics
            for m in metrics.metrics:
                value_num = m.value if isinstance(m.value, (int, float)) else None
                value_text = str(m.value) if not isinstance(m.value, (int, float)) else None

                conn.execute("""
                    INSERT INTO metrics
                    (analysis_id, name, value, value_text, metric_type, source, category, labels, unit, description, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.analysis_id,
                    m.name,
                    value_num,
                    value_text,
                    m.metric_type.value,
                    m.source.value,
                    m.category.value,
                    json.dumps({l.key: l.value for l in m.labels}),
                    m.unit,
                    m.description,
                    m.timestamp.isoformat(),
                ))

            conn.commit()
            logger.info(f"Saved {len(metrics.metrics)} metrics to SQLite")

    async def get_metrics(self, analysis_id: str) -> Optional[MetricSet]:
        """Load MetricSet from SQLite."""
        with self._get_conn() as conn:
            # Get analysis
            row = conn.execute(
                "SELECT * FROM analyses WHERE analysis_id = ?",
                (analysis_id,)
            ).fetchone()

            if not row:
                return None

            # Get metrics
            metrics_rows = conn.execute(
                "SELECT * FROM metrics WHERE analysis_id = ?",
                (analysis_id,)
            ).fetchall()

            from .schema import MetricType, MetricSource, MetricCategory, MetricLabel

            metrics_list = []
            for m in metrics_rows:
                value = m["value"] if m["value"] is not None else m["value_text"]
                labels_dict = json.loads(m["labels"]) if m["labels"] else {}

                metrics_list.append(Metric(
                    name=m["name"],
                    value=value,
                    metric_type=MetricType(m["metric_type"]),
                    source=MetricSource(m["source"]),
                    category=MetricCategory(m["category"]),
                    labels=[MetricLabel(k, v) for k, v in labels_dict.items()],
                    timestamp=datetime.fromisoformat(m["timestamp"]),
                    unit=m["unit"],
                    description=m["description"],
                ))

            return MetricSet(
                analysis_id=row["analysis_id"],
                repo_url=row["repo_url"],
                branch=row["branch"],
                collected_at=datetime.fromisoformat(row["collected_at"]),
                metrics=metrics_list,
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )

    async def list_analyses(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List analyses."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT analysis_id, repo_url, branch, collected_at, metrics_count
                FROM analyses
                ORDER BY collected_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()

            return [dict(row) for row in rows]

    async def query_metrics(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[Metric]:
        """Query metrics by name and filters."""
        with self._get_conn() as conn:
            query = "SELECT * FROM metrics WHERE name = ?"
            params = [metric_name]

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())

            query += " ORDER BY timestamp DESC"

            rows = conn.execute(query, params).fetchall()

            from .schema import MetricType, MetricSource, MetricCategory, MetricLabel

            results = []
            for m in rows:
                # Filter by labels if specified
                if labels:
                    m_labels = json.loads(m["labels"]) if m["labels"] else {}
                    if not all(m_labels.get(k) == v for k, v in labels.items()):
                        continue

                value = m["value"] if m["value"] is not None else m["value_text"]
                labels_dict = json.loads(m["labels"]) if m["labels"] else {}

                results.append(Metric(
                    name=m["name"],
                    value=value,
                    metric_type=MetricType(m["metric_type"]),
                    source=MetricSource(m["source"]),
                    category=MetricCategory(m["category"]),
                    labels=[MetricLabel(k, v) for k, v in labels_dict.items()],
                    timestamp=datetime.fromisoformat(m["timestamp"]),
                ))

            return results


class MetricsStore:
    """
    High-level metrics store with configurable backend.

    Usage:
        store = MetricsStore(backend="sqlite", path="/path/to/db.sqlite")
        await store.save(metrics)
        metrics = await store.get(analysis_id)
    """

    def __init__(
        self,
        backend: str = "json",
        path: Optional[Path] = None,
    ):
        self.backend_type = backend
        self.path = Path(path) if path else Path("./data/metrics")

        if backend == "json":
            self.backend = JSONFileStorage(self.path)
        elif backend == "sqlite":
            self.backend = SQLiteStorage(self.path / "metrics.db" if self.path.is_dir() else self.path)
        else:
            raise ValueError(f"Unknown backend: {backend}")

    async def save(self, metrics: MetricSet) -> None:
        """Save metrics."""
        await self.backend.save_metrics(metrics)

    async def get(self, analysis_id: str) -> Optional[MetricSet]:
        """Get metrics by analysis ID."""
        return await self.backend.get_metrics(analysis_id)

    async def list(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List all analyses."""
        return await self.backend.list_analyses(limit, offset)

    async def query(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[Metric]:
        """Query metrics."""
        return await self.backend.query_metrics(metric_name, start_time, end_time, labels)

    async def save_report(self, analysis_id: str, report_type: str, content: str) -> Optional[Path]:
        """Save a report (only for JSON backend)."""
        if isinstance(self.backend, JSONFileStorage):
            return await self.backend.save_report(analysis_id, report_type, content)
        return None


# Default store instance
metrics_store = MetricsStore(
    backend="json",
    path=Path(__file__).parent.parent / "data" / "metrics",
)
