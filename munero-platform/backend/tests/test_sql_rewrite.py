import unittest


class TestSQLRewrite(unittest.TestCase):
    def test_rewrites_postgres_client_name_equals_literal(self):
        from app.sql_rewrite import maybe_broaden_client_name_equals_to_contains

        sql = "SELECT 1 FROM fact_orders WHERE is_test = 0 AND client_name = 'loylogic';"
        out = maybe_broaden_client_name_equals_to_contains(
            sql,
            db_dialect="postgresql",
            params={"munero_start_date": "2025-01-01"},
        )
        self.assertIsNotNone(out)
        rewritten_sql, rewritten_params, warning = out  # type: ignore[misc]

        self.assertIn("client_name ILIKE '%loylogic%'", rewritten_sql)
        self.assertNotIn("client_name = 'loylogic'", rewritten_sql)
        self.assertEqual(rewritten_params, {"munero_start_date": "2025-01-01"})
        self.assertIsInstance(warning, str)

    def test_rewrites_preserves_alias(self):
        from app.sql_rewrite import maybe_broaden_client_name_equals_to_contains

        sql = "SELECT 1 FROM fact_orders fo WHERE fo.client_name = 'Loylogic Rewards FZE' AND fo.is_test = 0;"
        out = maybe_broaden_client_name_equals_to_contains(sql, db_dialect="postgresql")
        self.assertIsNotNone(out)
        rewritten_sql, rewritten_params, _warning = out  # type: ignore[misc]

        self.assertIn("fo.client_name ILIKE '%Loylogic Rewards FZE%'", rewritten_sql)
        self.assertEqual(rewritten_params, {})

    def test_rewrites_sqlite_uses_lower_like(self):
        from app.sql_rewrite import maybe_broaden_client_name_equals_to_contains

        sql = "SELECT 1 FROM fact_orders WHERE client_name = 'loylogic';"
        out = maybe_broaden_client_name_equals_to_contains(sql, db_dialect="sqlite")
        self.assertIsNotNone(out)
        rewritten_sql, rewritten_params, _warning = out  # type: ignore[misc]

        self.assertIn("LOWER(client_name) LIKE '%loylogic%'", rewritten_sql)
        self.assertEqual(rewritten_params, {})

    def test_does_not_rewrite_without_equality(self):
        from app.sql_rewrite import maybe_broaden_client_name_equals_to_contains

        sql = "SELECT 1 FROM fact_orders WHERE client_name ILIKE '%loylogic%';"
        self.assertIsNone(maybe_broaden_client_name_equals_to_contains(sql, db_dialect="postgresql"))

    def test_does_not_match_inside_comments_or_strings(self):
        from app.sql_rewrite import maybe_broaden_client_name_equals_to_contains

        sql_in_comment = "SELECT 1 FROM fact_orders -- client_name = 'loylogic'\nWHERE is_test = 0;"
        self.assertIsNone(maybe_broaden_client_name_equals_to_contains(sql_in_comment, db_dialect="postgresql"))

        sql_in_string = "SELECT 'client_name = ''loylogic''' AS example FROM fact_orders WHERE is_test = 0;"
        self.assertIsNone(maybe_broaden_client_name_equals_to_contains(sql_in_string, db_dialect="postgresql"))

    def test_normalizes_order_type_in_list(self):
        from app.sql_rewrite import rewrite_order_type_literals

        sql = "SELECT 1 FROM fact_orders WHERE order_type IN ('gift_cards','merchandise');"
        rewritten, warnings = rewrite_order_type_literals(sql)
        self.assertIn("order_type IN ('gift_card','merchandise')", rewritten)
        self.assertIn("Normalized order_type: gift_cards → gift_card", warnings)

    def test_normalizes_order_type_equals_literal(self):
        from app.sql_rewrite import rewrite_order_type_literals

        sql = "SELECT 1 FROM fact_orders WHERE order_type = 'Gift Cards';"
        rewritten, warnings = rewrite_order_type_literals(sql)
        self.assertIn("order_type = 'gift_card'", rewritten)
        self.assertIn("Normalized order_type: Gift Cards → gift_card", warnings)

    def test_order_type_rewrite_ignores_comments_and_strings(self):
        from app.sql_rewrite import rewrite_order_type_literals

        sql_in_comment = "SELECT 1 FROM fact_orders -- order_type IN ('gift_cards')\nWHERE is_test = 0;"
        rewritten_comment, warnings_comment = rewrite_order_type_literals(sql_in_comment)
        self.assertEqual(sql_in_comment, rewritten_comment)
        self.assertEqual(warnings_comment, [])

        sql_in_string = "SELECT 'order_type = ''gift_cards''' AS example FROM fact_orders WHERE is_test = 0;"
        rewritten_string, warnings_string = rewrite_order_type_literals(sql_in_string)
        self.assertEqual(sql_in_string, rewritten_string)
        self.assertEqual(warnings_string, [])

    def test_order_type_rewrite_no_change_when_canonical(self):
        from app.sql_rewrite import rewrite_order_type_literals

        sql = "SELECT 1 FROM fact_orders WHERE order_type IN ('gift_card','merchandise');"
        rewritten, warnings = rewrite_order_type_literals(sql)
        self.assertEqual(sql, rewritten)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
