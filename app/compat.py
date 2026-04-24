from __future__ import annotations

from datetime import datetime
from typing import Any, Callable


# ---- Pydantic compatibility ----
try:  # pragma: no cover
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    _MISSING = object()

    def Field(*, default: Any = _MISSING, default_factory: Callable[[], Any] | None = None) -> Any:
        if default_factory is not None:
            return default_factory()
        if default is not _MISSING:
            return default
        return None

    class BaseModel:
        def __init__(self, **kwargs: Any) -> None:
            annotations = getattr(self.__class__, "__annotations__", {})
            for key in annotations:
                if key in kwargs:
                    value = kwargs[key]
                elif hasattr(self.__class__, key):
                    value = getattr(self.__class__, key)
                else:
                    raise TypeError(f"Missing required field: {key}")
                setattr(self, key, value)

        def model_dump(self, mode: str | None = None) -> dict[str, Any]:
            data: dict[str, Any] = {}
            annotations = getattr(self.__class__, "__annotations__", {})
            for key in annotations:
                data[key] = _to_dict(getattr(self, key), mode=mode)
            return data

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}({self.model_dump()!r})"


def _to_dict(value: Any, mode: str | None = None) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode=mode)
    if isinstance(value, list):
        return [_to_dict(item, mode=mode) for item in value]
    if isinstance(value, dict):
        return {k: _to_dict(v, mode=mode) for k, v in value.items()}
    if mode == "json" and isinstance(value, datetime):
        return value.isoformat()
    return value


# ---- FastAPI compatibility ----
try:  # pragma: no cover
    from fastapi import FastAPI, HTTPException
except Exception:  # pragma: no cover
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class FastAPI:
        def __init__(self, title: str, version: str):
            self.title = title
            self.version = version

        def on_event(self, _: str):
            def decorator(func):
                return func

            return decorator

        def get(self, _: str, response_model: Any | None = None):
            def decorator(func):
                return func

            return decorator

        def post(self, _: str, response_model: Any | None = None):
            def decorator(func):
                return func

            return decorator
