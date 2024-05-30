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
    
    def test_negation(self):
        query = table("table").select(-lit(3))
        self.assertEqual(query.sql, "SELECT -3 FROM table")

    def test_isin(self):
        query = table("table").where(col("id").is_in(1,2,3)).select("*")
        self.assertEqual(query.sql, "SELECT * FROM table WHERE id IN ( 1, 2, 3 )")

        query = table("table").where(col("id").is_in(lit(2), lit(4))).select("*")
        self.assertEqual(query.sql, "SELECT * FROM table WHERE id IN ( 2, 4 )")

    def test_isin_query(self):
        inner_query = table("t1").where(col("`date`") > lit('2024-01-01')).select("id")
        query = table("t2").where(col("id").is_in(inner_query)).select("id")
        print(query.sql)

    def test_tuple(self):
        query = table("t1").where(tup(col("id"), col("date")).is_in(lit(123), lit('2024-01-01'))).select("id")
        self.assertEqual(query.sql, "SELECT id FROM t1 WHERE ( id, date ) IN ( 123, '2024-01-01' )")
    
    def test_examples(self):
        t = table("db.schema.customers").select(
            col("id"), 
            (col("first_name") == lit("john")).as_("is_john"),
            (col("last_name") == lit("doe")).as_("is_doe"),
            (col("age") - col("years_since_joined")).as_("`age when joined`")
        )
        self.assertEqual(t.sql, """SELECT id, first_name = 'john' AS is_john, last_name = 'doe' AS is_doe, age - years_since_joined AS `age when joined` FROM db.schema.customers""")





    