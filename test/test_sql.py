from sparkit.sql import *

from unittest import TestCase

class TestSql(TestCase):

    def test_wilcard_is_default(self):
        t = table("some.table")
        self.assertEqual(t.sql, "SELECT * FROM some.table")
    
    def test_single_col(self):
        t = table("some.table").select(col("a"))
        self.assertEqual(t.sql, "SELECT a FROM some.table")

    def test_expr(self):
        t = table("some.table").select(expr("foo(2, 2)").as_("calc"))
        self.assertEqual(t.sql, "SELECT foo(2, 2) AS calc FROM some.table")

    def test_interval(self):
        t = table("some.table").select(col("date") + interval(2).DAY)
        self.assertEqual(t.sql, "SELECT date + INTERVAL 2 DAY FROM some.table")

    def test_interval_conversion(self):
        t = table("some.table").select(col("date") + interval(2).DAY.to("MINUTE"))
        self.assertEqual(t.sql, "SELECT date + INTERVAL 2 DAY TO MINUTE FROM some.table")

    def test_column_cast(self):
        c = col("a").cast.DATE
        self.assertEqual(c.expr.sql, 'CAST( a AS DATE )')
        self.assertEqual(c.cast.BIGDECIMAL.expr.sql, 'CAST( CAST( a AS DATE ) AS BIGNUMERIC )')
    
    def test_examples(self):
        t = table("db.schema.customers").select(
            col("id"), 
            (col("first_name") == lit("john")).as_("is_john"),
            (col("last_name") == lit("doe")).as_("is_doe"),
            (col("age") - col("years_since_joined")).as_("`age when joined`")
        )
        print(t.sql)