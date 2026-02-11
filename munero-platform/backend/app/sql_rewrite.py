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


def _escape_sql_string_literal(value: str) -> str:
    return value.replace("'", "''")


def canonicalize_order_type(value: str) -> str | None:
    """
    Normalize common user/LLM variants to canonical `order_type` values.

    Canonical values:
    - gift_card
    - merchandise
    """
    if not isinstance(value, str):
        return None

    lowered = value.strip().lower()
    if not lowered:
        return None

    normalized = "".join(ch for ch in lowered if ch not in {" ", "-", "_"})
    if normalized in {"giftcard", "giftcards"}:
        return "gift_card"
    if normalized in {"merch", "merchandise"}:
        return "merchandise"
    return None


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

    if (db_dialect or "").lower() == "postgresql":
        pattern = f"%{literal_value}%"
        replacement = f"{column_ref} ILIKE '{_escape_sql_string_literal(pattern)}'"
    else:
        pattern = f"%{literal_value.lower()}%"
        replacement = f"LOWER({column_ref}) LIKE '{_escape_sql_string_literal(pattern)}'"

    rewritten_sql = f"{sql[:match_start]}{replacement}{sql[match_end:]}"
    warning = "Broadened client match to a case-insensitive substring after exact match returned no rows."
    return rewritten_sql, rewritten_params, warning


def rewrite_order_type_literals(sql: str) -> tuple[str, list[str]]:
    """
    Rewrite known `order_type` literal variants to canonical enum values.

    Only rewrites the following patterns (outside comments/quotes/dollar-quotes):
    - order_type = '<literal>'
    - order_type IN ('<lit1>', '<lit2>', ...)
    """
    if not isinstance(sql, str) or not sql:
        return sql, []

    warnings: list[str] = []
    upper_sql = sql.upper()
    needle = "ORDER_TYPE"

    state = "code"
    dollar_delim: str | None = None
    out_parts: list[str] = []
    i = 0

    while i < len(sql):
        ch = sql[i]

        if state == "code":
            end = i + len(needle)
            if end <= len(sql) and upper_sql.startswith(needle, i):
                before_ok = i == 0 or not _is_identifier_char(sql[i - 1])
                after_ok = end == len(sql) or not _is_identifier_char(sql[end])
                if before_ok and after_ok:
                    j = _skip_ws(sql, end)
                    j = _skip_type_cast(sql, j)
                    j = _skip_ws(sql, j)

                    # Pattern 1: order_type = '<literal>'
                    if j < len(sql) and sql[j] == "=":
                        k = _skip_ws(sql, j + 1)
                        literal = _parse_single_quoted_literal(sql, k)
                        if literal is not None:
                            literal_end, literal_value = literal
                            canonical = canonicalize_order_type(literal_value)
                            if canonical is not None and canonical != literal_value:
                                out_parts.append(sql[i:k])
                                out_parts.append(f"'{_escape_sql_string_literal(canonical)}'")
                                warnings.append(
                                    f"Normalized order_type: {literal_value} → {canonical}"
                                )
                                i = literal_end
                                continue

                    # Pattern 2: order_type IN ('<lit1>', '<lit2>', ...)
                    if j + 2 <= len(sql) and upper_sql.startswith("IN", j):
                        in_end = j + 2
                        after_in_ok = in_end == len(sql) or not _is_identifier_char(sql[in_end])
                        if after_in_ok:
                            k = _skip_ws(sql, in_end)
                            if k < len(sql) and sql[k] == "(":
                                k += 1
                                replacements: list[tuple[int, int, str, str]] = []
                                list_end: int | None = None
                                parse_ok = True
                                while True:
                                    k = _skip_ws(sql, k)
                                    if k >= len(sql):
                                        parse_ok = False
                                        break
                                    if sql[k] == ")":
                                        list_end = k + 1
                                        break

                                    literal = _parse_single_quoted_literal(sql, k)
                                    if literal is None:
                                        parse_ok = False
                                        break

                                    literal_end, literal_value = literal
                                    canonical = canonicalize_order_type(literal_value)
                                    if canonical is not None and canonical != literal_value:
                                        replacements.append(
                                            (k, literal_end, literal_value, canonical)
                                        )

                                    k = _skip_type_cast(sql, literal_end)
                                    k = _skip_ws(sql, k)
                                    if k >= len(sql):
                                        parse_ok = False
                                        break
                                    if sql[k] == ",":
                                        k += 1
                                        continue
                                    if sql[k] == ")":
                                        list_end = k + 1
                                        break
                                    parse_ok = False
                                    break

                                if parse_ok and list_end is not None and replacements:
                                    seg_pos = i
                                    for lit_start, lit_end, original, canonical in replacements:
                                        out_parts.append(sql[seg_pos:lit_start])
                                        out_parts.append(
                                            f"'{_escape_sql_string_literal(canonical)}'"
                                        )
                                        warnings.append(
                                            f"Normalized order_type: {original} → {canonical}"
                                        )
                                        seg_pos = lit_end
                                    out_parts.append(sql[seg_pos:list_end])
                                    i = list_end
                                    continue

            if ch == "'":
                state = "single_quote"
                out_parts.append(ch)
                i += 1
                continue
            if ch == '"':
                state = "double_quote"
                out_parts.append(ch)
                i += 1
                continue
            if ch == "-" and i + 1 < len(sql) and sql[i + 1] == "-":
                state = "line_comment"
                out_parts.append(sql[i : i + 2])
                i += 2
                continue
            if ch == "/" and i + 1 < len(sql) and sql[i + 1] == "*":
                state = "block_comment"
                out_parts.append(sql[i : i + 2])
                i += 2
                continue
            if ch == "$":
                delim = _match_postgres_dollar_quote_delimiter(sql, i)
                if delim:
                    state = "dollar_quote"
                    dollar_delim = delim
                    out_parts.append(delim)
                    i += len(delim)
                    continue

            out_parts.append(ch)
            i += 1
            continue

        if state == "single_quote":
            out_parts.append(ch)
            if ch == "'":
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    out_parts.append("'")
                    i += 2
                    continue
                state = "code"
            i += 1
            continue

        if state == "double_quote":
            out_parts.append(ch)
            if ch == '"':
                if i + 1 < len(sql) and sql[i + 1] == '"':
                    out_parts.append('"')
                    i += 2
                    continue
                state = "code"
            i += 1
            continue

        if state == "line_comment":
            out_parts.append(ch)
            if ch == "\n":
                state = "code"
            i += 1
            continue

        if state == "block_comment":
            out_parts.append(ch)
            if ch == "*" and i + 1 < len(sql) and sql[i + 1] == "/":
                out_parts.append("/")
                i += 2
                state = "code"
                continue
            i += 1
            continue

        if state == "dollar_quote":
            if dollar_delim and sql.startswith(dollar_delim, i):
                out_parts.append(dollar_delim)
                i += len(dollar_delim)
                state = "code"
                dollar_delim = None
                continue
            out_parts.append(ch)
            i += 1
            continue

        out_parts.append(ch)
        i += 1

    return "".join(out_parts), warnings
