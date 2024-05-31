from unittest import TestCase

from fluq.expression.base import *
from fluq.expression.operator import *
from fluq.expression.join import *
from fluq.expression.clause import FromClauseExpression, SelectClauseExpression
from fluq.expression.query import QueryExpression
from fluq.expression.selectable import ColumnExpression

class TestJoin(TestCase):

    def test_join_operation(self):
        
        inner = InnerJoinOperationExpression(left=TableNameExpression("t1"), right=TableNameExpression("t2"))
        self.assertEqual(inner.sql, "t1 INNER JOIN t2")
        self.assertEqual(inner.tokens(), ['t1', 'INNER JOIN', 't2'])

        inner = InnerJoinOperationExpression(
            left=TableNameExpression("t1"), 
            right=TableNameExpression("t2"),
            left_alias="a")
        
        self.assertEqual(inner.sql, "t1 AS a INNER JOIN t2")
        self.assertListEqual(inner.tokens(), ['t1', 'AS', 'a', 'INNER JOIN', 't2'])

        left = LeftJoinOperationExpression(
            left=TableNameExpression("t1"), 
            right=TableNameExpression("t2"),
            left_alias="a", right_alias="b")
        
        self.assertEqual(left.sql, "t1 AS a LEFT OUTER JOIN t2 AS b")
        self.assertListEqual(left.tokens(), ['t1', 'AS', 'a', 'LEFT OUTER JOIN', 't2', 'AS', 'b'])

        left_on = LeftJoinOperationExpression(
            left=TableNameExpression("t1"), 
            right=TableNameExpression("t2"),
            left_alias="a", right_alias="b", on=Equal(ColumnExpression("a.id"), ColumnExpression("b.id")))
        
        self.assertEqual(left_on.sql, "t1 AS a LEFT OUTER JOIN t2 AS b ON a.id = b.id")
        self.assertListEqual(left_on.tokens(), ['t1', 'AS', 'a', 'LEFT OUTER JOIN', 't2', 'AS', 'b', 'ON', 'a.id', '=' ,'b.id'])

    def test_join_nested(self):

        first = InnerJoinOperationExpression(
            left=TableNameExpression("t1"), 
            right=TableNameExpression("t2"),
            on=Equal(ColumnExpression("t1.id"), ColumnExpression("t2.id")))
        
        nested = InnerJoinOperationExpression(
            left=first,
            right=TableNameExpression("t3"),
            on=Equal(ColumnExpression("t3.id"), ColumnExpression("t2.id")))
        

        self.assertEqual(nested.sql, "t1 INNER JOIN t2 ON t1.id = t2.id INNER JOIN t3 ON t3.id = t2.id")
        self.assertListEqual(nested.tokens(), ['t1', 'INNER JOIN', 't2', 'ON', 't1.id', '=', 't2.id', 'INNER JOIN', 't3', 'ON', 't3.id', '=', 't2.id'])

    def test_join_subquery(self):
        query = QueryExpression(
            from_clause=FromClauseExpression(table="db.schema.table1"),
            select_clause=SelectClauseExpression([ColumnExpression("a"), ColumnExpression("b")], [None, None])
            )
        inner = InnerJoinOperationExpression(left=query, right=TableNameExpression("t2"), left_alias="A", 
                                             on=Equal(ColumnExpression("A.a"), ColumnExpression("t2.a")))
        expected = ["(", "SELECT", "a", ",", "b", "FROM", "db.schema.table1",")", "AS", "A", "INNER JOIN", "t2", "ON", "A.a", "=", "t2.a"]
        
        self.assertListEqual(inner.tokens(), expected)

    def test_cross_join_no_on_clause(self):

        cross = CrossJoinOperationExpression(
            left=TableNameExpression("t1"), 
            right=TableNameExpression("t2"),
            left_alias="A", right_alias="B"
        )

        self.assertEqual(cross.sql, "t1 AS A CROSS JOIN t2 AS B")
        self.assertListEqual(cross.tokens(), ['t1', 'AS', 'A', 'CROSS JOIN', 't2', 'AS', 'B'])