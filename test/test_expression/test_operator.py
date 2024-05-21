from unittest import TestCase

from sparkit.expression.base import *
from sparkit.expression.operator import *
from sparkit.expression.query import QueryExpression
from sparkit.expression.clause import FromClauseExpression, SelectClauseExpression

class TestOperator(TestCase):

    def test_logical_and_math_expressions(self):
        zipped = [
            (Equal(LiteralExpression(1), LiteralExpression("a")), "1 = 'a'"),
            (NotEqual(LiteralExpression(1), LiteralExpression("a")), "1 <> 'a'"),
            (Greater(LiteralExpression(1), LiteralExpression("a")), "1 > 'a'"),
            (GreaterOrEqual(LiteralExpression(1), LiteralExpression("a")), "1 >= 'a'"),
            (Less(LiteralExpression(1), LiteralExpression("a")), "1 < 'a'"),
            (LessOrEqual(LiteralExpression(1), LiteralExpression("a")), "1 <= 'a'"),
            (In(ColumnExpression("a"), 1, 2, 4.5, 55), "a IN (1, 2, 4.5, 55)"),
            (In(ColumnExpression("a"), True, False), "a IN (TRUE, FALSE)"),
            (In(ColumnExpression("a"), 'yo yo', 'ya ya', 'ye ye'), "a IN ('yo yo', 'ya ya', 'ye ye')"),
            (Not(ColumnExpression("a")), 'a <> TRUE'),
            (Not(LiteralExpression(False)), 'FALSE <> TRUE'),
            (IsNull(ColumnExpression("a")), 'a IS NULL'),
            (IsNotNull(ColumnExpression("a")), 'a IS NOT NULL'),
            (Between(ColumnExpression("a"), LiteralExpression(1), LiteralExpression(2)), 'a BETWEEN 1 AND 2'),
            (And(
                Equal(LiteralExpression(1), LiteralExpression("a")), 
                NotEqual(LiteralExpression(1), LiteralExpression("a"))
            ), "(1 = 'a') AND (1 <> 'a')"),
            (Or(Equal(LiteralExpression(1), LiteralExpression("a")), 
                NotEqual(LiteralExpression(1), LiteralExpression("a"))
            ), "(1 = 'a') OR (1 <> 'a')"),
            (Like(ColumnExpression("a"), LiteralExpression("%%abs")), "a LIKE '%%abs'"),
            (Plus(ColumnExpression("a"), ColumnExpression("b")), "a + b"),
            (Minus(ColumnExpression("a"), ColumnExpression("b")), "a - b"),
            (Multiply(ColumnExpression("a"), ColumnExpression("b")), "a * b"),
            (Divide(ColumnExpression("a"), ColumnExpression("b")), "a / b"),
        ]
        for result, expected in zipped:
            self.assertEqual(result.sql, expected)

    def test_in_query_expression(self):
        query = QueryExpression(
            from_clause=FromClauseExpression(table="db.schema.table1"),
            select_clause=SelectClauseExpression([ColumnExpression("id")], [None])
            )
        expr = In(ColumnExpression("a"), query)
        expected = "a IN ( SELECT id\nFROM db.schema.table1 )"
        self.assertEqual(expr.sql, expected)