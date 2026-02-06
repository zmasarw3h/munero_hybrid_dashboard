"""
Logging helpers that avoid leaking sensitive payloads by default.

These utilities are intentionally dependency-free and safe to call from API
endpoints and core services.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any, Optional


_WHITESPACE_RE = re.compile(r"\s+")


def short_sha256(text: str, *, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def redact_sql_for_log(
    sql: Optional[str],
    *,
    max_chars: int = 160,
    include_prefix: bool = False,
) -> str:
    """
    Return a compact, non-sensitive SQL representation for logs.

    By default this logs only length + sha. Optionally include a whitespace-
    collapsed prefix (never the full query).
    """
    if not sql:
        return "len=0 sha=<none>"

    sql_text = str(sql)
    parts = [f"len={len(sql_text)}", f"sha={short_sha256(sql_text)}"]

    if include_prefix:
        head = _WHITESPACE_RE.sub(" ", sql_text.strip())[:max_chars]
        parts.append(f"head={head!r}")

    return " ".join(parts)


def redact_filter_values_for_log(filters: Any) -> dict[str, Any]:
    """
    Redact filter values for logs.

    - Never logs list contents; logs counts instead.
    - Dates are converted to ISO strings.
    """
    if filters is None:
        return {}

    if hasattr(filters, "model_dump"):
        raw: Any = filters.model_dump()
    elif isinstance(filters, Mapping):
        raw = dict(filters)
    elif hasattr(filters, "dict"):
        raw = filters.dict()
    else:
        return {"<filters>": "<unserializable>"}

    redacted: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            redacted[key] = {"count": len(value)}
            continue
        if isinstance(value, (date, datetime)):
            redacted[key] = value.isoformat()
            continue
        redacted[key] = value

    return redacted


def redact_params_for_log(params: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """
    Redact SQL parameter payloads for logs.

    - Never logs list values; logs counts instead.
    - Avoids logging raw strings; logs their lengths.
    """
    if not params:
        return {}

    redacted: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, list):
            redacted[key] = {"type": "list", "count": len(value)}
        elif isinstance(value, (date, datetime)):
            redacted[key] = value.isoformat()
        elif isinstance(value, str):
            redacted[key] = {"type": "str", "len": len(value)}
        else:
            redacted[key] = value

    return redacted

