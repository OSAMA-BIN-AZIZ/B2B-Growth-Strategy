from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import settings

DB_PATH = Path("data/b2b_growth.db")


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


class BaseStorage:
    def init_db(self) -> None: ...

    def insert_article(self, payload: dict) -> int: ...

    def list_articles(self) -> list[dict]: ...

    def insert_draft(self, payload: dict) -> int: ...

    def get_draft(self, draft_id: int) -> dict | None: ...

    def insert_metric(self, payload: dict) -> int: ...

    def list_metric_summary(self) -> list[dict]: ...

    def topic_feedback_boost(self) -> dict[str, float]: ...

    def insert_publish_job(self, payload: dict) -> int: ...

    def update_publish_job(self, job_id: int, status: str, external_id: str | None, message: str | None) -> None: ...

    def get_publish_job(self, job_id: int) -> dict | None: ...


class SqliteStorage(BaseStorage):
    def __init__(self, path: Path):
        self.path = path

    def _conn(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS articles (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  subtitle TEXT,
                  body TEXT NOT NULL,
                  published_at TEXT,
                  views INTEGER DEFAULT 0,
                  likes INTEGER DEFAULT 0,
                  shares INTEGER DEFAULT 0,
                  lead_effect TEXT,
                  target_customer TEXT NOT NULL,
                  topic TEXT NOT NULL,
                  pain_point TEXT NOT NULL,
                  product_relation TEXT,
                  has_inquiry INTEGER DEFAULT 0,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS drafts (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic_title TEXT NOT NULL,
                  outline_json TEXT NOT NULL,
                  markdown TEXT NOT NULL,
                  html TEXT NOT NULL,
                  wechat_title TEXT NOT NULL,
                  wechat_summary TEXT NOT NULL,
                  cover_copy TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS metrics (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  article_id INTEGER,
                  topic_title TEXT NOT NULL,
                  pain_point TEXT NOT NULL,
                  views INTEGER DEFAULT 0,
                  likes INTEGER DEFAULT 0,
                  shares INTEGER DEFAULT 0,
                  inquiries INTEGER DEFAULT 0,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS publish_jobs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  draft_id INTEGER NOT NULL,
                  channel TEXT NOT NULL,
                  status TEXT NOT NULL,
                  external_id TEXT,
                  message TEXT,
                  created_at TEXT NOT NULL
                );
                """
            )

    def insert_article(self, payload: dict) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO articles
                (title, subtitle, body, published_at, views, likes, shares, lead_effect,
                 target_customer, topic, pain_point, product_relation, has_inquiry, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["title"],
                    payload.get("subtitle"),
                    payload["body"],
                    payload.get("published_at"),
                    payload.get("views", 0),
                    payload.get("likes", 0),
                    payload.get("shares", 0),
                    payload.get("lead_effect"),
                    payload["target_customer"],
                    payload["topic"],
                    payload["pain_point"],
                    payload.get("product_relation"),
                    int(payload.get("has_inquiry", False)),
                    _utc_now(),
                ),
            )
            return int(cur.lastrowid)

    def list_articles(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM articles ORDER BY id DESC").fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["has_inquiry"] = bool(item["has_inquiry"])
            result.append(item)
        return result

    def insert_draft(self, payload: dict) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO drafts
                (topic_title, outline_json, markdown, html, wechat_title, wechat_summary, cover_copy, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["topic_title"],
                    json.dumps(payload["outline"], ensure_ascii=False),
                    payload["markdown"],
                    payload["html"],
                    payload["wechat_title"],
                    payload["wechat_summary"],
                    payload["cover_copy"],
                    _utc_now(),
                ),
            )
            return int(cur.lastrowid)

    def get_draft(self, draft_id: int) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["outline"] = json.loads(item.pop("outline_json"))
        return item

    def insert_metric(self, payload: dict) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO metrics
                (article_id, topic_title, pain_point, views, likes, shares, inquiries, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("article_id"),
                    payload["topic_title"],
                    payload["pain_point"],
                    payload.get("views", 0),
                    payload.get("likes", 0),
                    payload.get("shares", 0),
                    payload.get("inquiries", 0),
                    _utc_now(),
                ),
            )
            return int(cur.lastrowid)

    def list_metric_summary(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT pain_point,
                       COUNT(*) AS records,
                       AVG(views) AS avg_views,
                       AVG(likes) AS avg_likes,
                       AVG(shares) AS avg_shares,
                       AVG(inquiries) AS avg_inquiries
                FROM metrics
                GROUP BY pain_point
                ORDER BY avg_inquiries DESC, avg_shares DESC
                """
            ).fetchall()

        summary = []
        for row in rows:
            item = dict(row)
            item["avg_views"] = round(item["avg_views"] or 0.0, 2)
            item["avg_likes"] = round(item["avg_likes"] or 0.0, 2)
            item["avg_shares"] = round(item["avg_shares"] or 0.0, 2)
            item["avg_inquiries"] = round(item["avg_inquiries"] or 0.0, 2)
            item["feedback_boost"] = round(min(10.0, item["avg_inquiries"] * 2 + item["avg_shares"] * 0.1), 2)
            summary.append(item)
        return summary

    def topic_feedback_boost(self) -> dict[str, float]:
        return {item["pain_point"]: item["feedback_boost"] for item in self.list_metric_summary()}

    def insert_publish_job(self, payload: dict) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO publish_jobs (draft_id, channel, status, external_id, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["draft_id"],
                    payload["channel"],
                    payload["status"],
                    payload.get("external_id"),
                    payload.get("message"),
                    _utc_now(),
                ),
            )
            return int(cur.lastrowid)

    def update_publish_job(self, job_id: int, status: str, external_id: str | None, message: str | None) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE publish_jobs SET status = ?, external_id = ?, message = ? WHERE id = ?",
                (status, external_id, message, job_id),
            )

    def get_publish_job(self, job_id: int) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM publish_jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


class PostgresStorage(BaseStorage):
    def __init__(self, dsn: str):
        try:
            import psycopg
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("PostgreSQL backend requires psycopg installed") from exc
        self.psycopg = psycopg
        self.dsn = dsn

    def _conn(self):
        return self.psycopg.connect(self.dsn)

    def init_db(self) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                  id SERIAL PRIMARY KEY,
                  title TEXT NOT NULL,
                  subtitle TEXT,
                  body TEXT NOT NULL,
                  published_at TEXT,
                  views INTEGER DEFAULT 0,
                  likes INTEGER DEFAULT 0,
                  shares INTEGER DEFAULT 0,
                  lead_effect TEXT,
                  target_customer TEXT NOT NULL,
                  topic TEXT NOT NULL,
                  pain_point TEXT NOT NULL,
                  product_relation TEXT,
                  has_inquiry BOOLEAN DEFAULT FALSE,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS drafts (
                  id SERIAL PRIMARY KEY,
                  topic_title TEXT NOT NULL,
                  outline_json JSONB NOT NULL,
                  markdown TEXT NOT NULL,
                  html TEXT NOT NULL,
                  wechat_title TEXT NOT NULL,
                  wechat_summary TEXT NOT NULL,
                  cover_copy TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metrics (
                  id SERIAL PRIMARY KEY,
                  article_id INTEGER,
                  topic_title TEXT NOT NULL,
                  pain_point TEXT NOT NULL,
                  views INTEGER DEFAULT 0,
                  likes INTEGER DEFAULT 0,
                  shares INTEGER DEFAULT 0,
                  inquiries INTEGER DEFAULT 0,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS publish_jobs (
                  id SERIAL PRIMARY KEY,
                  draft_id INTEGER NOT NULL,
                  channel TEXT NOT NULL,
                  status TEXT NOT NULL,
                  external_id TEXT,
                  message TEXT,
                  created_at TEXT NOT NULL
                );
                """
            )

    def insert_article(self, payload: dict) -> int:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO articles
                (title, subtitle, body, published_at, views, likes, shares, lead_effect,
                 target_customer, topic, pain_point, product_relation, has_inquiry, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload["title"],
                    payload.get("subtitle"),
                    payload["body"],
                    payload.get("published_at"),
                    payload.get("views", 0),
                    payload.get("likes", 0),
                    payload.get("shares", 0),
                    payload.get("lead_effect"),
                    payload["target_customer"],
                    payload["topic"],
                    payload["pain_point"],
                    payload.get("product_relation"),
                    payload.get("has_inquiry", False),
                    _utc_now(),
                ),
            )
            return int(cur.fetchone()[0])

    def list_articles(self) -> list[dict]:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM articles ORDER BY id DESC")
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def insert_draft(self, payload: dict) -> int:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO drafts
                (topic_title, outline_json, markdown, html, wechat_title, wechat_summary, cover_copy, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload["topic_title"],
                    json.dumps(payload["outline"], ensure_ascii=False),
                    payload["markdown"],
                    payload["html"],
                    payload["wechat_title"],
                    payload["wechat_summary"],
                    payload["cover_copy"],
                    _utc_now(),
                ),
            )
            return int(cur.fetchone()[0])

    def get_draft(self, draft_id: int) -> dict | None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM drafts WHERE id = %s", (draft_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [d.name for d in cur.description]
            item = dict(zip(cols, row))
            item["outline"] = item.pop("outline_json")
            if isinstance(item["outline"], str):
                item["outline"] = json.loads(item["outline"])
            return item

    def insert_metric(self, payload: dict) -> int:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO metrics
                (article_id, topic_title, pain_point, views, likes, shares, inquiries, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload.get("article_id"),
                    payload["topic_title"],
                    payload["pain_point"],
                    payload.get("views", 0),
                    payload.get("likes", 0),
                    payload.get("shares", 0),
                    payload.get("inquiries", 0),
                    _utc_now(),
                ),
            )
            return int(cur.fetchone()[0])

    def list_metric_summary(self) -> list[dict]:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT pain_point,
                       COUNT(*) AS records,
                       AVG(views)::float AS avg_views,
                       AVG(likes)::float AS avg_likes,
                       AVG(shares)::float AS avg_shares,
                       AVG(inquiries)::float AS avg_inquiries
                FROM metrics
                GROUP BY pain_point
                ORDER BY avg_inquiries DESC, avg_shares DESC
                """
            )
            cols = [d.name for d in cur.description]
            summary = [dict(zip(cols, row)) for row in cur.fetchall()]
        for item in summary:
            item["feedback_boost"] = round(min(10.0, item["avg_inquiries"] * 2 + item["avg_shares"] * 0.1), 2)
        return summary

    def topic_feedback_boost(self) -> dict[str, float]:
        return {item["pain_point"]: item["feedback_boost"] for item in self.list_metric_summary()}

    def insert_publish_job(self, payload: dict) -> int:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO publish_jobs (draft_id, channel, status, external_id, message, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload["draft_id"],
                    payload["channel"],
                    payload["status"],
                    payload.get("external_id"),
                    payload.get("message"),
                    _utc_now(),
                ),
            )
            return int(cur.fetchone()[0])

    def update_publish_job(self, job_id: int, status: str, external_id: str | None, message: str | None) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE publish_jobs SET status = %s, external_id = %s, message = %s WHERE id = %s",
                (status, external_id, message, job_id),
            )

    def get_publish_job(self, job_id: int) -> dict | None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM publish_jobs WHERE id = %s", (job_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [d.name for d in cur.description]
            return dict(zip(cols, row))


def _build_storage() -> BaseStorage:
    url = settings.database_url
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return PostgresStorage(url)
    return SqliteStorage(DB_PATH)


_STORAGE = _build_storage()


def init_db() -> None:
    _STORAGE.init_db()


def insert_article(payload: dict) -> int:
    return _STORAGE.insert_article(payload)


def list_articles() -> list[dict]:
    return _STORAGE.list_articles()


def insert_draft(payload: dict) -> int:
    return _STORAGE.insert_draft(payload)


def get_draft(draft_id: int) -> dict | None:
    return _STORAGE.get_draft(draft_id)


def insert_metric(payload: dict) -> int:
    return _STORAGE.insert_metric(payload)


def list_metric_summary() -> list[dict]:
    return _STORAGE.list_metric_summary()


def topic_feedback_boost() -> dict[str, float]:
    return _STORAGE.topic_feedback_boost()


def insert_publish_job(payload: dict) -> int:
    return _STORAGE.insert_publish_job(payload)


def update_publish_job(job_id: int, status: str, external_id: str | None, message: str | None) -> None:
    _STORAGE.update_publish_job(job_id, status, external_id, message)


def get_publish_job(job_id: int) -> dict | None:
    return _STORAGE.get_publish_job(job_id)
