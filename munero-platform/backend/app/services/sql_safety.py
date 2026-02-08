"""
SQL safety validator for user/LLM-provided queries.

Rules:
- Must be a single statement (one optional trailing semicolon allowed).
- Must start with SELECT or WITH (after leading whitespace/comments).
- Must not contain common DDL/DML keywords (case-insensitive).

This is intentionally lightweight (no external SQL parser dependency).
"""

from __future__ import annotations

import re
from typing import Final, Iterable


class SQLSafetyError(ValueError):
    """Raised when a SQL string fails safety validation."""


_STARTS_WITH_SELECT_OR_WITH: Final[re.Pattern[str]] = re.compile(r"^(SELECT|WITH)\b", re.IGNORECASE)

_BANNED_KEYWORDS: Final[tuple[str, ...]] = (
    # DML
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "REPLACE",
    "UPSERT",
    # DDL / schema + admin
    "CREATE",
    "ALTER",
    "DROP",
    "TRUNCATE",
    "RENAME",
    "GRANT",
    "REVOKE",
    # Potentially dangerous/side-effectful
    "EXEC",
    "EXECUTE",
    "CALL",
    "INTO",  # SELECT ... INTO can create tables in some dialects
    "VACUUM",
    "PRAGMA",
    "ATTACH",
    "DETACH",
    "COPY",
)

_BANNED_KEYWORDS_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in _BANNED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def validate_sql_safety(sql: str, *, banned_keywords: Iterable[str] = _BANNED_KEYWORDS) -> None:
    """
    Validate that `sql` is a read-only single-statement SELECT/WITH query.

    Raises:
        SQLSafetyError: When the query violates any safety rule.
    """
    if not isinstance(sql, str) or not sql.strip():
        raise SQLSafetyError("SQL query is empty.")

    masked = _mask_comments_and_literals(sql)
    candidate = masked.strip()
    if not candidate:
        raise SQLSafetyError("SQL query is empty.")

    # Single-statement only (allow one trailing semicolon).
    candidate_no_trailing_semicolon = candidate
    if candidate_no_trailing_semicolon.endswith(";"):
        candidate_no_trailing_semicolon = candidate_no_trailing_semicolon[:-1].rstrip()
    if ";" in candidate_no_trailing_semicolon:
        raise SQLSafetyError("Only a single SQL statement is allowed.")

    if not _STARTS_WITH_SELECT_OR_WITH.match(candidate_no_trailing_semicolon.lstrip()):
        raise SQLSafetyError("Only SELECT or WITH statements are allowed.")

    banned_re = (
        _BANNED_KEYWORDS_RE
        if banned_keywords is _BANNED_KEYWORDS
        else re.compile(
            r"\b(?:" + "|".join(re.escape(k) for k in banned_keywords) + r")\b",
            re.IGNORECASE,
        )
    )

    match = banned_re.search(candidate_no_trailing_semicolon)
    if match:
        raise SQLSafetyError(f"Query contains forbidden keyword: {match.group(0).upper()}.")


def _mask_comments_and_literals(sql: str) -> str:
    """
    Replace SQL comments and quoted strings/identifiers with whitespace.

    This keeps token boundaries stable while ensuring validation doesn't
    accidentally match keywords inside quoted sections.
    """
    out: list[str] = []
    i = 0
    n = len(sql)

    while i < n:
        ch = sql[i]

        # Line comment: -- ... (until newline)
        if ch == "-" and i + 1 < n and sql[i + 1] == "-":
            out.append(" ")
            i += 2
            while i < n and sql[i] not in "\r\n":
                i += 1
            continue

        # MySQL-style line comment: # ...
        if ch == "#":
            out.append(" ")
            i += 1
            while i < n and sql[i] not in "\r\n":
                i += 1
            continue

        # Block comment: /* ... */
        if ch == "/" and i + 1 < n and sql[i + 1] == "*":
            out.append(" ")
            i += 2
            while i + 1 < n and not (sql[i] == "*" and sql[i + 1] == "/"):
                i += 1
            i = i + 2 if i + 1 < n else n
            continue

        # Single-quoted string literal: '...'
        if ch == "'":
            out.append(" ")
            i += 1
            while i < n:
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":  # escaped quote
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue

        # Double-quoted identifier: "..."
        if ch == '"':
            out.append(" ")
            i += 1
            while i < n:
                if sql[i] == '"':
                    if i + 1 < n and sql[i + 1] == '"':  # escaped quote
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue

        # Backtick-quoted identifier: `...`
        if ch == "`":
            out.append(" ")
            i += 1
            while i < n:
                if sql[i] == "`":
                    if i + 1 < n and sql[i + 1] == "`":  # escaped quote
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue

        # Bracket-quoted identifier: [...]
        if ch == "[":
            out.append(" ")
            i += 1
            while i < n:
                if sql[i] == "]":
                    if i + 1 < n and sql[i + 1] == "]":  # escaped bracket
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)
