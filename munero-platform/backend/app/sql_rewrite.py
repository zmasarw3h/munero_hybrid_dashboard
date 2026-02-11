"""
Deterministic SQL rewrites for common "LLM got it almost right" cases.

These helpers are intentionally lightweight and do not depend on third-party
SQL parsers. They operate on *single statements* that have already passed the
 project's SQL safety validation.
"""

from __future__ import annotations

from typing import Any


def _is_identifier_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _match_postgres_dollar_quote_delimiter(text: str, start: int) -> str | None:
    if start >= len(text) or text[start] != "$":
        return None

    end = text.find("$", start + 1)
    if end == -1:
        return None

    tag = text[start + 1 : end]
    if any((not (ch.isalnum() or ch == "_")) for ch in tag):
        return None

    return text[start : end + 1]


def _skip_ws(sql: str, idx: int) -> int:
    i = idx
    while i < len(sql) and sql[i].isspace():
        i += 1
    return i


def _skip_type_cast(sql: str, idx: int) -> int:
    i = idx
    while True:
        i = _skip_ws(sql, i)
        if not sql.startswith("::", i):
            return i
        i += 2
        while i < len(sql) and (sql[i].isalnum() or sql[i] in "_."):
            i += 1


def _parse_single_quoted_literal(sql: str, idx: int) -> tuple[int, str] | None:
    if idx >= len(sql) or sql[idx] != "'":
        return None

    i = idx + 1
    out_chars: list[str] = []
    while i < len(sql):
        ch = sql[i]
        if ch == "'":
            if i + 1 < len(sql) and sql[i + 1] == "'":
                out_chars.append("'")
                i += 2
                continue
            return i + 1, "".join(out_chars)
        out_chars.append(ch)
        i += 1
    return None


def _find_client_name_equals_literal(sql: str) -> tuple[int, int, str, str] | None:
    upper_sql = sql.upper()
    needle = "CLIENT_NAME"

    state = "code"
    dollar_delim: str | None = None
    i = 0

    while i < len(sql):
        ch = sql[i]

        if state == "code":
            end = i + len(needle)
            if end <= len(sql) and upper_sql.startswith(needle, i):
                before_ok = i == 0 or not _is_identifier_char(sql[i - 1])
                after_ok = end == len(sql) or not _is_identifier_char(sql[end])
                if before_ok and after_ok:
                    match_start = i
                    if i > 0 and sql[i - 1] == ".":
                        j = i - 2
                        while j >= 0 and _is_identifier_char(sql[j]):
                            j -= 1
                        if j + 1 < i - 1:
                            match_start = j + 1

                    column_ref_end = end
                    column_ref = sql[match_start:column_ref_end]

                    j = _skip_ws(sql, column_ref_end)
                    j = _skip_type_cast(sql, j)
                    j = _skip_ws(sql, j)
                    if j >= len(sql) or sql[j] != "=":
                        i += 1
                        continue

                    j = _skip_ws(sql, j + 1)
                    literal = _parse_single_quoted_literal(sql, j)
                    if literal is None:
                        i += 1
                        continue

                    literal_end, literal_value = literal
                    k = _skip_type_cast(sql, literal_end)
                    return match_start, k, column_ref, literal_value

            if ch == "'":
                state = "single_quote"
                i += 1
                continue
            if ch == '"':
                state = "double_quote"
                i += 1
                continue
            if ch == "-" and i + 1 < len(sql) and sql[i + 1] == "-":
                state = "line_comment"
                i += 2
                continue
            if ch == "/" and i + 1 < len(sql) and sql[i + 1] == "*":
                state = "block_comment"
                i += 2
                continue
            if ch == "$":
                delim = _match_postgres_dollar_quote_delimiter(sql, i)
                if delim:
                    state = "dollar_quote"
                    dollar_delim = delim
                    i += len(delim)
                    continue

            i += 1
            continue

        if state == "single_quote":
            if ch == "'":
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    i += 2
                    continue
                state = "code"
                i += 1
                continue
            i += 1
            continue

        if state == "double_quote":
            if ch == '"':
                if i + 1 < len(sql) and sql[i + 1] == '"':
                    i += 2
                    continue
                state = "code"
                i += 1
                continue
            i += 1
            continue

        if state == "line_comment":
            if ch == "\n":
                state = "code"
            i += 1
            continue

        if state == "block_comment":
            if ch == "*" and i + 1 < len(sql) and sql[i + 1] == "/":
                state = "code"
                i += 2
                continue
            i += 1
            continue

        if state == "dollar_quote":
            if dollar_delim and sql.startswith(dollar_delim, i):
                state = "code"
                i += len(dollar_delim)
                dollar_delim = None
                continue
            i += 1
            continue

        i += 1

    return None


def maybe_broaden_client_name_equals_to_contains(
    sql: str,
    *,
    db_dialect: str,
    params: dict[str, Any] | None = None,
    param_base: str = "munero_client_name_contains",
) -> tuple[str, dict[str, Any], str] | None:
    """
    Rewrite `client_name = '<literal>'` to a case-insensitive substring match.

    Returns:
        (rewritten_sql, rewritten_params, warning) if a rewrite applies, else None.
    """
    if not isinstance(sql, str) or not sql.strip():
        return None

    found = _find_client_name_equals_literal(sql)
    if found is None:
        return None

    match_start, match_end, column_ref, literal_value = found
    if not literal_value:
        return None

    rewritten_params = dict(params or {})
    key = param_base
    suffix = 2
    while key in rewritten_params:
        key = f"{param_base}_{suffix}"
        suffix += 1
    rewritten_params[key] = literal_value

    if (db_dialect or "").lower() == "postgresql":
        replacement = f"{column_ref} ILIKE '%' || :{key} || '%'"
    else:
        replacement = f"LOWER({column_ref}) LIKE '%' || LOWER(:{key}) || '%'"

    rewritten_sql = f"{sql[:match_start]}{replacement}{sql[match_end:]}"
    warning = "Broadened client match to a case-insensitive substring after exact match returned no rows."
    return rewritten_sql, rewritten_params, warning

