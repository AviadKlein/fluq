from __future__ import annotations
from unittest import TestCase

from fluq.expression.base import *
from fluq.expression.operator import *
from fluq.expression.clause import *
from fluq.expression.function import *
from fluq.expression.query import *
from fluq.expression.selectable import ColumnExpression


class TestQuery(TestCase):

    def test_query_expression(self):
        query = QueryExpression(
            from_clause=FromClauseExpression(table="db.schema.table1"),
            select_clause=SelectClauseExpression([ColumnExpression("a"), ColumnExpression("b")], [None, None])
            )
        expected = """SELECT a, b FROM db.schema.table1"""
        self.assertEqual(query.sql, expected)
        self.assertListEqual(query.tokens(), ['SELECT', 'a', ',', 'b', 'FROM', 'db.schema.table1'])




        

    

        
        
