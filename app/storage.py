from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable

DB_PATH = Path("data/b2b_growth.db")


@contextmanager
def get_conn() -> Iterable[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
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
            """
        )
        conn.commit()


def insert_article(payload: dict) -> int:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
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
                now,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_articles() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM articles ORDER BY id DESC").fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["has_inquiry"] = bool(item["has_inquiry"])
        result.append(item)
    return result


def insert_draft(payload: dict) -> int:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
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
                now,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_draft(draft_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["outline"] = json.loads(item.pop("outline_json"))
    return item
