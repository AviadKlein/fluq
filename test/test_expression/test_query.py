from __future__ import annotations
from unittest import TestCase

from sparkit.expression.base import *
from sparkit.expression.operator import *
from sparkit.expression.clause import *
from sparkit.expression.function import *
from sparkit.expression.query import *
from sparkit.expression.selectable import ColumnExpression


class TestQuery(TestCase):

    def test_query_expression(self):
        query = QueryExpression(
            from_clause=FromClauseExpression(table="db.schema.table1"),
            select_clause=SelectClauseExpression([ColumnExpression("a"), ColumnExpression("b")], [None, None])
            )
        expected = """SELECT a, b FROM db.schema.table1"""
        self.assertEqual(query.sql, expected)
        self.assertListEqual(query.tokens(), ['SELECT', 'a', ',', 'b', 'FROM', 'db.schema.table1'])




        

    

        
        
