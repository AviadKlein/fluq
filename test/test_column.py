from unittest import TestCase

from sparkit.column import *
from sparkit.sql import *


class TestColumn(TestCase):

    def test_init(self):
        c = col("a")
        self.assertEqual(c.expr.sql, "a")
        self.assertIsNone(c.alias)
        self.assertTrue(isinstance(c.expr, ColumnExpression))

        c = Column(name="a")
        self.assertEqual(c.expr.sql, "a")
        self.assertIsNone(c.alias)
        self.assertTrue(isinstance(c.expr, ColumnExpression))

        c = Column(name="a", alias="b")
        self.assertEqual(c.expr.sql, "a")
        self.assertEqual(c.alias, "b")
        self.assertTrue(isinstance(c.expr, ColumnExpression))

        c = Column(expression=LiteralExpression(3))
        self.assertEqual(c.expr.sql, "3")
        self.assertIsNone(c.alias)
        self.assertTrue(isinstance(c.expr, LiteralExpression))

        c = Column(expression=LiteralExpression(3), alias="id")
        self.assertEqual(c.expr.sql, "3")
        self.assertEqual(c.alias, "id")
        self.assertTrue(isinstance(c.expr, LiteralExpression))

        c = lit(3).as_("id")
        self.assertEqual(c.expr.sql, "3")
        self.assertEqual(c.alias, "id")
        self.assertTrue(isinstance(c.expr, LiteralExpression))

    def test_logicals(self):

        a = col("a")
        b = col("b")
        result: Column = a == b
        self.assertTrue(isinstance(result, Column))
        self.assertTrue(isinstance(result.expr, Equal))
        self.assertEqual(result.expr.sql, "a = b")

        result: Column = a == 1
        self.assertTrue(isinstance(result, Column))
        self.assertEqual(result.expr.sql, "a = 1")
        self.assertEqual(result.expr.right, LiteralExpression(1))

        result: Column = a != b
        self.assertTrue(isinstance(result.expr, NotEqual))
        self.assertEqual(result.expr.sql, "a <> b")

        self.assertEqual((a > b).expr.sql, "a > b")
        self.assertEqual((a > lit(1)).expr.sql, "a > 1")
        self.assertEqual((a > 1).expr.sql, "a > 1")

        self.assertEqual((a >= b).expr.sql, "a >= b")
        self.assertEqual((a >= 0).expr.sql, "a >= 0")

        self.assertEqual((a < b).expr.sql, "a < b")
        self.assertEqual((a < -10).expr.sql, "a < -10")
        
        self.assertEqual((a <= b).expr.sql, "a <= b")
        self.assertEqual((a <= 1e3).expr.sql, "a <= 1000.0")
        self.assertEqual((a <= 10_000).expr.sql, "a <= 10000")

        self.assertEqual(a.is_not_null().expr.sql, "a IS NOT NULL")
        self.assertEqual(a.is_null().expr.sql, "a IS NULL")

        self.assertEqual(a.between(2, 3).expr.sql, "a BETWEEN 2 AND 3")
        self.assertEqual(a.between(lit(2), lit(3)).expr.sql, "a BETWEEN 2 AND 3")

        self.assertEqual(((a <= b) & (b < 5)).expr.sql, "(a <= b) AND (b < 5)")
        self.assertEqual(((a <= b) | (b < 5)).expr.sql, "(a <= b) OR (b < 5)")

        self.assertEqual(a.like("%%foobar").expr.sql, "a LIKE '%%foobar'")

    def test_math(self):

        a = col("a")
        b = col("b")

        # unary negation
        self.assertEqual((-a).expr.sql, "-a")
        self.assertTrue(isinstance(-a, Column))
        self.assertTrue(isinstance((-a).expr, NegatedExpression))

        # arithmetic
        self.assertEqual((a + b).expr.sql, "a + b")
        self.assertEqual((a - b).expr.sql, "a - b")
        self.assertEqual((a * b).expr.sql, "a * b")
        self.assertEqual((a / b).expr.sql, "a / b")
        self.assertEqual((a // b).expr.sql, "FLOOR(a / b)")
        self.assertEqual((a % b).expr.sql, "MOD(a, b)")

        self.assertEqual((a + 5).expr.sql, "a + 5")
        self.assertEqual((a - 5).expr.sql, "a - 5")
        self.assertEqual((a * 5).expr.sql, "a * 5")
        self.assertEqual((a / 5).expr.sql, "a / 5")
        self.assertEqual((a // 5).expr.sql, "FLOOR(a / 5)")
        self.assertEqual((a % 5).expr.sql, "MOD(a, 5)")


    def test_case_expr(self):
        # case expressions
        case_ = when(col("a") > 5, 0).when(col("a") > 100, 1).otherwise(-1)
        expr: CaseExpression = case_.expr

        expected = [
            'WHEN a > 5 THEN 0',
            'WHEN a > 100 THEN 1',
            'ELSE -1'
        ]
        result = expr.cases_unindented_sql()
        self.assertListEqual(expected, result)

    def test_functions(self):
        
        result = functions.mod(col("a"), col("b"))
        self.assertEqual(result.expr.sql, "MOD(a, b)")

        result = functions.floor(lit(1.2))
        self.assertEqual(result.expr.sql, "FLOOR(1.2)")

        result = functions.current_date()
        self.assertEqual(result.expr.sql, "CURRENT_DATE()")

        result = functions.sum(col("a"))
        self.assertEqual(result.expr.sql, "SUM(a)")

        result = functions.sum(col("a"))
        self.assertEqual(result.expr.sql, "SUM(a)")

    def test_ordering(self):
        
        c = col("a")
        self.assertTrue(c.order_by_spec.asc)
        self.assertEqual(c.order_by_spec.nulls, "FIRST")

        c = col("a").asc(nulls="LAST")
        self.assertTrue(c.order_by_spec.asc)
        self.assertEqual(c.order_by_spec.nulls, "LAST")

        c = col("a").desc()
        self.assertFalse(c.order_by_spec.asc)
        self.assertEqual(c.order_by_spec.nulls, "FIRST")

        c = col("a").desc(nulls="LAST")
        self.assertFalse(c.order_by_spec.asc)
        self.assertEqual(c.order_by_spec.nulls, "LAST")

        # keeps nulls spec when changing order
        c = Column(
            expression=ColumnExpression("a"), 
            alias="a", 
            order_by_spec=OrderBySpecExpression(asc=True, nulls="LAST")
            )
        c = c.desc()
        self.assertEqual(c.order_by_spec.nulls, "LAST")

    def test_window_spec(self):
        ws = WindowSpec() # empty init
        result = ws._to_expr().unindented_sql()
        self.assertEqual(result, "")

        ws = WindowSpec().partition_by("a", "b")
        result = ws._to_expr().unindented_sql()
        self.assertEqual(result, "PARTITION BY a, b")
        

        ws = WindowSpec().partition_by(col("a"), col("b"))
        result = ws._to_expr().unindented_sql()
        self.assertEqual(result, "PARTITION BY a, b")

        ws = WindowSpec().partition_by(col("a"), col("b")).order_by("a")
        result = ws._to_expr().unindented_sql()
        self.assertEqual(result, "PARTITION BY a, b ORDER BY a ASC NULLS FIRST")

        ws = WindowSpec().partition_by(col("a"), col("b")).order_by(col("a").desc(nulls="last"))
        result = ws._to_expr().unindented_sql()
        self.assertEqual(result, "PARTITION BY a, b ORDER BY a DESC NULLS LAST")

        ws = (
            WindowSpec().partition_by(col("a"), col("b"))
            .order_by(col("a").desc(nulls="last")).rows_between(None, 0)
            )
        
        result = ws._to_expr().unindented_sql()
        expected = 'PARTITION BY a, b ORDER BY a DESC NULLS LAST ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW'
        self.assertEqual(result, expected)

        # SQL example
        t = (
            table("db.schema.payments").as_("p")
            .group_by(col("player"), col("date"))
            .agg(
                functions.sum(col("value")).as_("sum_value"),
                functions.sum(col("value")).over(WindowSpec().partition_by("player")).as_("total_per_player"),
                functions.sum(col("value")).over(WindowSpec().partition_by("player").order_by("date").rows_between(-5,5)).as_("running_window")
                )
        )
        result = t.sql.split('\n')
        print(result)
        expected = ['SELECT player, date, SUM(value) AS sum_value, SUM(value) OVER(PARTITION BY player) AS total_per_player, SUM(value) OVER(PARTITION BY player ORDER BY date ASC NULLS FIRST ROWS BETWEEN 5 PRECEDING AND 5 FOLLOWING) AS running_window', 
                    'FROM db.schema.payments', 
                    'GROUP BY player, date']
        self.assertEqual(result, expected)


        with self.assertRaises(SyntaxError) as cm:
            WindowSpec().partition_by("player").rows_between(-5,5)._to_expr()
        self.assertEqual(
            str(cm.exception), 
            "If a WindowFrameExpression is defined in a WindowSpecExpression, and order_by object needs to be defined as well"
            )
        




        
        
        