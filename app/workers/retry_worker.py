from __future__ import annotations

import argparse

from app.main import retry_failed_publish_jobs
from app.storage import init_db


def run_once(limit: int = 20, delay_minutes: int = 10) -> dict:
    init_db()
    result = retry_failed_publish_jobs(limit=limit, delay_minutes=delay_minutes)
    return result.model_dump() if hasattr(result, "model_dump") else result.__dict__


def main() -> None:
    parser = argparse.ArgumentParser(description="Run WeChat publish retry worker once")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--delay-minutes", type=int, default=10)
    args = parser.parse_args()
    print(run_once(limit=args.limit, delay_minutes=args.delay_minutes))


if __name__ == "__main__":
    main()
