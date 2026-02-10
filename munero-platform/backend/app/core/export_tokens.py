"""
Signed tokens for guarding sensitive operations (e.g., chat CSV export).

These tokens are intended to be:
- short-lived
- verifiable server-side (HMAC)
- bound to the specific SQL + filters payload

No external dependencies.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


class ExportTokenError(ValueError):
    """Raised when an export token is missing, invalid, or expired."""


def normalize_sql_for_token(sql_query: str) -> str:
    sql = (sql_query or "").strip()
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()
    return sql


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    raw = (data or "").strip()
    if not raw:
        raise ExportTokenError("Export token signature is missing.")
    padding = "=" * ((4 - len(raw) % 4) % 4)
    try:
        return base64.urlsafe_b64decode(raw + padding)
    except Exception as exc:  # pragma: no cover - defensive
        raise ExportTokenError("Export token signature is malformed.") from exc


def _canonical_json(obj: object) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def _sign(secret: str, message: bytes) -> bytes:
    key = (secret or "").encode("utf-8")
    if not key:
        raise ExportTokenError("Export signing secret is not configured.")
    return hmac.new(key, message, hashlib.sha256).digest()


def make_export_token(
    *,
    secret: str,
    sql_query: str,
    filters: dict[str, Any] | None,
    ttl_s: int = 900,
    now_epoch: int | None = None,
) -> str:
    now = int(time.time()) if now_epoch is None else int(now_epoch)
    exp = now + max(0, int(ttl_s))

    payload = {
        "v": 1,
        "exp": exp,
        "sql": normalize_sql_for_token(sql_query),
        "filters": filters or {},
    }
    message = _canonical_json(payload).encode("utf-8")
    signature = _sign(secret, message)
    return f"{exp}.{_b64url_encode(signature)}"


def verify_export_token(
    *,
    secret: str,
    token: str,
    sql_query: str,
    filters: dict[str, Any] | None,
    now_epoch: int | None = None,
) -> None:
    raw = (token or "").strip()
    if not raw:
        raise ExportTokenError("Export token is missing.")

    exp_part, sep, sig_part = raw.partition(".")
    if not sep:
        raise ExportTokenError("Export token is malformed.")

    try:
        exp = int(exp_part)
    except ValueError as exc:
        raise ExportTokenError("Export token expiry is malformed.") from exc

    now = int(time.time()) if now_epoch is None else int(now_epoch)
    if exp < now:
        raise ExportTokenError("Export token has expired.")

    payload = {
        "v": 1,
        "exp": exp,
        "sql": normalize_sql_for_token(sql_query),
        "filters": filters or {},
    }
    message = _canonical_json(payload).encode("utf-8")
    expected = _sign(secret, message)
    actual = _b64url_decode(sig_part)
    if not hmac.compare_digest(expected, actual):
        raise ExportTokenError("Export token is invalid.")

