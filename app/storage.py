from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings

DB_PATH = Path("data/b2b_growth.db")


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


def _after_minutes(minutes: int) -> str:
    return (datetime.utcnow() + timedelta(minutes=minutes)).isoformat()


class BaseStorage:
    def init_db(self) -> None: ...

    def insert_article(self, payload: dict) -> int: ...

    def list_articles(self) -> list[dict]: ...

    def insert_draft(self, payload: dict) -> int: ...

    def get_draft(self, draft_id: int) -> dict | None: ...

    def insert_metric(self, payload: dict) -> int: ...

    def list_metric_summary(self) -> list[dict]: ...

    def topic_feedback_boost(self) -> dict[str, float]: ...

    def list_topic_recommendations(self, top_n: int = 5) -> list[dict]: ...

    def list_segmented_topic_recommendations(self, top_n: int = 5, target_customer: str | None = None, industry: str | None = None, growth_stage: str | None = None) -> list[dict]: ...

    def insert_publish_job(self, payload: dict) -> int: ...

    def update_publish_job(self, job_id: int, status: str, external_id: str | None, message: str | None) -> None: ...

    def get_publish_job(self, job_id: int) -> dict | None: ...

    def get_publish_job_by_idempotency(self, channel: str, idempotency_key: str) -> dict | None: ...

    def list_publish_jobs(self, limit: int = 50) -> list[dict]: ...

    def list_retryable_publish_jobs(self, limit: int = 20) -> list[dict]: ...

    def mark_retry_scheduled(self, job_id: int, delay_minutes: int, message: str) -> None: ...

    def insert_audit_log(self, payload: dict) -> int: ...

    def list_audit_logs(self, limit: int = 50) -> list[dict]: ...

    def insert_llm_log(self, payload: dict) -> int: ...

    def list_llm_logs(self, limit: int = 50) -> list[dict]: ...


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
                  target_customer TEXT,
                  industry TEXT,
                  growth_stage TEXT,
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
                  idempotency_key TEXT,
                  retry_count INTEGER DEFAULT 0,
                  max_retries INTEGER DEFAULT 3,
                  next_retry_at TEXT,
                  created_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS ux_publish_jobs_channel_key
                ON publish_jobs(channel, idempotency_key);

                CREATE TABLE IF NOT EXISTS audit_logs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  draft_id INTEGER NOT NULL,
                  action TEXT NOT NULL,
                  actor TEXT NOT NULL,
                  note TEXT,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS llm_logs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  model TEXT NOT NULL,
                  operation TEXT NOT NULL,
                  latency_ms INTEGER DEFAULT 0,
                  success INTEGER DEFAULT 0,
                  error TEXT,
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
                (article_id, topic_title, pain_point, target_customer, industry, growth_stage, views, likes, shares, inquiries, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("article_id"),
                    payload["topic_title"],
                    payload["pain_point"],
                    payload.get("target_customer"),
                    payload.get("industry"),
                    payload.get("growth_stage"),
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

    def list_topic_recommendations(self, top_n: int = 5) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT topic_title,
                       pain_point,
                       COUNT(*) AS records,
                       AVG(views) AS avg_views,
                       AVG(shares) AS avg_shares,
                       AVG(inquiries) AS avg_inquiries
                FROM metrics
                GROUP BY topic_title, pain_point
                ORDER BY avg_inquiries DESC, avg_shares DESC, avg_views DESC
                LIMIT ?
                """,
                (top_n,),
            ).fetchall()

        recs = []
        for row in rows:
            item = dict(row)
            avg_views = float(item["avg_views"] or 0.0)
            avg_shares = float(item["avg_shares"] or 0.0)
            avg_inquiries = float(item["avg_inquiries"] or 0.0)
            item["suggestion_score"] = round(avg_inquiries * 0.6 + avg_shares * 0.3 + (avg_views / 1000) * 0.1, 2)
            recs.append(item)
        return sorted(recs, key=lambda x: x["suggestion_score"], reverse=True)

    def list_segmented_topic_recommendations(self, top_n: int = 5, target_customer: str | None = None, industry: str | None = None, growth_stage: str | None = None) -> list[dict]:
        clauses = []
        args: list[str | int] = []
        if target_customer:
            clauses.append("target_customer = ?")
            args.append(target_customer)
        if industry:
            clauses.append("industry = ?")
            args.append(industry)
        if growth_stage:
            clauses.append("growth_stage = ?")
            args.append(growth_stage)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT topic_title, pain_point, COUNT(*) AS records,
                   AVG(views) AS avg_views, AVG(shares) AS avg_shares, AVG(inquiries) AS avg_inquiries
            FROM metrics
            {where_sql}
            GROUP BY topic_title, pain_point
            ORDER BY avg_inquiries DESC, avg_shares DESC, avg_views DESC
            LIMIT ?
        """
        args.append(top_n)
        with self._conn() as conn:
            rows = conn.execute(sql, tuple(args)).fetchall()

        recs = []
        for row in rows:
            item = dict(row)
            item["suggestion_score"] = round((item["avg_inquiries"] or 0) * 0.6 + (item["avg_shares"] or 0) * 0.3 + ((item["avg_views"] or 0) / 1000) * 0.1, 2)
            recs.append(item)
        return sorted(recs, key=lambda x: x["suggestion_score"], reverse=True)

    def insert_publish_job(self, payload: dict) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO publish_jobs (draft_id, channel, status, external_id, message, idempotency_key, retry_count, max_retries, next_retry_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["draft_id"],
                    payload["channel"],
                    payload["status"],
                    payload.get("external_id"),
                    payload.get("message"),
                    payload.get("idempotency_key"),
                    payload.get("retry_count", 0),
                    payload.get("max_retries", 3),
                    payload.get("next_retry_at"),
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

    def get_publish_job_by_idempotency(self, channel: str, idempotency_key: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM publish_jobs WHERE channel = ? AND idempotency_key = ? ORDER BY id DESC LIMIT 1",
                (channel, idempotency_key),
            ).fetchone()
        return dict(row) if row else None

    def list_publish_jobs(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM publish_jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def list_retryable_publish_jobs(self, limit: int = 20) -> list[dict]:
        now = _utc_now()
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM publish_jobs
                WHERE status = 'failed'
                  AND retry_count < max_retries
                  AND (next_retry_at IS NULL OR next_retry_at <= ?)
                ORDER BY id ASC
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_retry_scheduled(self, job_id: int, delay_minutes: int, message: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE publish_jobs
                SET retry_count = retry_count + 1,
                    status = 'failed',
                    message = ?,
                    next_retry_at = ?
                WHERE id = ?
                """,
                (message, _after_minutes(delay_minutes), job_id),
            )

    def insert_audit_log(self, payload: dict) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO audit_logs (draft_id, action, actor, note, created_at) VALUES (?, ?, ?, ?, ?)",
                (payload["draft_id"], payload["action"], payload["actor"], payload.get("note"), _utc_now()),
            )
            return int(cur.lastrowid)

    def list_audit_logs(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def insert_llm_log(self, payload: dict) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO llm_logs (model, operation, latency_ms, success, error, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (payload["model"], payload["operation"], payload.get("latency_ms", 0), int(payload.get("success", False)), payload.get("error"), _utc_now()),
            )
            return int(cur.lastrowid)

    def list_llm_logs(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM llm_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        data = [dict(r) for r in rows]
        for item in data:
            item["success"] = bool(item["success"])
        return data


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
                  target_customer TEXT,
                  industry TEXT,
                  growth_stage TEXT,
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
                  idempotency_key TEXT,
                  retry_count INTEGER DEFAULT 0,
                  max_retries INTEGER DEFAULT 3,
                  next_retry_at TEXT,
                  created_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS ux_publish_jobs_channel_key
                ON publish_jobs(channel, idempotency_key);

                CREATE TABLE IF NOT EXISTS audit_logs (
                  id SERIAL PRIMARY KEY,
                  draft_id INTEGER NOT NULL,
                  action TEXT NOT NULL,
                  actor TEXT NOT NULL,
                  note TEXT,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS llm_logs (
                  id SERIAL PRIMARY KEY,
                  model TEXT NOT NULL,
                  operation TEXT NOT NULL,
                  latency_ms INTEGER DEFAULT 0,
                  success BOOLEAN DEFAULT FALSE,
                  error TEXT,
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
                (article_id, topic_title, pain_point, target_customer, industry, growth_stage, views, likes, shares, inquiries, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload.get("article_id"),
                    payload["topic_title"],
                    payload["pain_point"],
                    payload.get("target_customer"),
                    payload.get("industry"),
                    payload.get("growth_stage"),
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

    def list_topic_recommendations(self, top_n: int = 5) -> list[dict]:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT topic_title,
                       pain_point,
                       COUNT(*) AS records,
                       AVG(views)::float AS avg_views,
                       AVG(shares)::float AS avg_shares,
                       AVG(inquiries)::float AS avg_inquiries
                FROM metrics
                GROUP BY topic_title, pain_point
                ORDER BY avg_inquiries DESC, avg_shares DESC, avg_views DESC
                LIMIT %s
                """,
                (top_n,),
            )
            cols = [d.name for d in cur.description]
            recs = [dict(zip(cols, row)) for row in cur.fetchall()]
        for item in recs:
            item["suggestion_score"] = round(item["avg_inquiries"] * 0.6 + item["avg_shares"] * 0.3 + (item["avg_views"] / 1000) * 0.1, 2)
        return sorted(recs, key=lambda x: x["suggestion_score"], reverse=True)

    def list_segmented_topic_recommendations(self, top_n: int = 5, target_customer: str | None = None, industry: str | None = None, growth_stage: str | None = None) -> list[dict]:
        clauses = []
        args: list[str | int] = []
        if target_customer:
            clauses.append("target_customer = %s")
            args.append(target_customer)
        if industry:
            clauses.append("industry = %s")
            args.append(industry)
        if growth_stage:
            clauses.append("growth_stage = %s")
            args.append(growth_stage)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT topic_title, pain_point, COUNT(*) AS records,
                   AVG(views)::float AS avg_views, AVG(shares)::float AS avg_shares, AVG(inquiries)::float AS avg_inquiries
            FROM metrics
            {where_sql}
            GROUP BY topic_title, pain_point
            ORDER BY avg_inquiries DESC, avg_shares DESC, avg_views DESC
            LIMIT %s
        """
        args.append(top_n)
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(args))
            cols = [d.name for d in cur.description]
            recs = [dict(zip(cols, row)) for row in cur.fetchall()]
        for item in recs:
            item["suggestion_score"] = round((item["avg_inquiries"] or 0) * 0.6 + (item["avg_shares"] or 0) * 0.3 + ((item["avg_views"] or 0) / 1000) * 0.1, 2)
        return sorted(recs, key=lambda x: x["suggestion_score"], reverse=True)

    def insert_publish_job(self, payload: dict) -> int:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO publish_jobs (draft_id, channel, status, external_id, message, idempotency_key, retry_count, max_retries, next_retry_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload["draft_id"],
                    payload["channel"],
                    payload["status"],
                    payload.get("external_id"),
                    payload.get("message"),
                    payload.get("idempotency_key"),
                    payload.get("retry_count", 0),
                    payload.get("max_retries", 3),
                    payload.get("next_retry_at"),
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

    def get_publish_job_by_idempotency(self, channel: str, idempotency_key: str) -> dict | None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM publish_jobs WHERE channel = %s AND idempotency_key = %s ORDER BY id DESC LIMIT 1",
                (channel, idempotency_key),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d.name for d in cur.description]
            return dict(zip(cols, row))

    def list_publish_jobs(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM publish_jobs ORDER BY id DESC LIMIT %s", (limit,))
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def list_retryable_publish_jobs(self, limit: int = 20) -> list[dict]:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM publish_jobs
                WHERE status = 'failed'
                  AND retry_count < max_retries
                  AND (next_retry_at IS NULL OR next_retry_at <= %s)
                ORDER BY id ASC
                LIMIT %s
                """,
                (_utc_now(), limit),
            )
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def mark_retry_scheduled(self, job_id: int, delay_minutes: int, message: str) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE publish_jobs
                SET retry_count = retry_count + 1,
                    status = 'failed',
                    message = %s,
                    next_retry_at = %s
                WHERE id = %s
                """,
                (message, _after_minutes(delay_minutes), job_id),
            )

    def insert_audit_log(self, payload: dict) -> int:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit_logs (draft_id, action, actor, note, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (payload["draft_id"], payload["action"], payload["actor"], payload.get("note"), _utc_now()),
            )
            return int(cur.fetchone()[0])

    def list_audit_logs(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT %s", (limit,))
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def insert_llm_log(self, payload: dict) -> int:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO llm_logs (model, operation, latency_ms, success, error, created_at) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (payload["model"], payload["operation"], payload.get("latency_ms", 0), payload.get("success", False), payload.get("error"), _utc_now()),
            )
            return int(cur.fetchone()[0])

    def list_llm_logs(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM llm_logs ORDER BY id DESC LIMIT %s", (limit,))
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


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


def list_topic_recommendations(top_n: int = 5) -> list[dict]:
    return _STORAGE.list_topic_recommendations(top_n)


def list_segmented_topic_recommendations(top_n: int = 5, target_customer: str | None = None, industry: str | None = None, growth_stage: str | None = None) -> list[dict]:
    return _STORAGE.list_segmented_topic_recommendations(top_n, target_customer, industry, growth_stage)


def insert_publish_job(payload: dict) -> int:
    return _STORAGE.insert_publish_job(payload)


def update_publish_job(job_id: int, status: str, external_id: str | None, message: str | None) -> None:
    _STORAGE.update_publish_job(job_id, status, external_id, message)


def get_publish_job(job_id: int) -> dict | None:
    return _STORAGE.get_publish_job(job_id)


def get_publish_job_by_idempotency(channel: str, idempotency_key: str) -> dict | None:
    return _STORAGE.get_publish_job_by_idempotency(channel, idempotency_key)


def list_publish_jobs(limit: int = 50) -> list[dict]:
    return _STORAGE.list_publish_jobs(limit)


def list_retryable_publish_jobs(limit: int = 20) -> list[dict]:
    return _STORAGE.list_retryable_publish_jobs(limit)


def mark_retry_scheduled(job_id: int, delay_minutes: int, message: str) -> None:
    _STORAGE.mark_retry_scheduled(job_id, delay_minutes, message)


def insert_audit_log(payload: dict) -> int:
    return _STORAGE.insert_audit_log(payload)


def list_audit_logs(limit: int = 50) -> list[dict]:
    return _STORAGE.list_audit_logs(limit)


def insert_llm_log(payload: dict) -> int:
    return _STORAGE.insert_llm_log(payload)


def list_llm_logs(limit: int = 50) -> list[dict]:
    return _STORAGE.list_llm_logs(limit)
