from unittest import TestCase

from fluq.expression.base import *
from fluq.expression.literals import OrderBySpecExpression
from fluq.expression.operator import *
from fluq.expression.join import *
from fluq.expression.clause import *
from fluq.expression.query import QueryExpression
from fluq.expression.selectable import ColumnExpression, LiteralExpression

class TestClause(TestCase):
    
    def test_select_clause_wildcard(self):
        select = SelectClauseExpression.from_args(ColumnExpression("*"))
        self.assertEqual(select.sql, "SELECT *")
        self.assertListEqual(select.tokens(), ['SELECT', '*'])

        select = select.add(ColumnExpression("t1"), "a")
        self.assertEqual(select.sql, "SELECT *, t1 AS a")
        self.assertListEqual(select.tokens(), ['SELECT', '*', ',', 't1', 'AS', 'a'])
   
    def test_select_clause_exceptions(self):
        with self.assertRaises(AssertionError) as cm:
            SelectClauseExpression.from_args((ColumnExpression("*"), "A"))
        self.assertEqual(str(cm.exception), """ColumnExpression("*") can't have an alias, got 'A'""")

        with self.assertRaises(AssertionError) as cm:
             select = SelectClauseExpression.from_args(ColumnExpression("*"))
             select.add(ColumnExpression("*"))
        self.assertEqual(str(cm.exception), """can only have 1 ColumnExpression("*")""")

    def test_select_expressions(self):
        select = SelectClauseExpression([],[]).add(LiteralExpression(1), 'a').add(ColumnExpression("b"))
        self.assertListEqual(select.tokens(), ['SELECT', '1', 'AS', 'a', ',', 'b'])

    def test_select_distinct(self):
        select = SelectClauseExpression.from_args((ColumnExpression("a"), None), (ColumnExpression("b"), None))
        select = select.distinct()
        self.assertListEqual(select.tokens(), ['SELECT', 'DISTINCT', 'a', ',', 'b'])

    def test_from_clause(self):
        fc = FromClauseExpression(table="db.schema.table1")
        self.assertEqual(fc.sql, "FROM db.schema.table1")
        self.assertListEqual(fc.tokens(), ['FROM', 'db.schema.table1'])
        self.assertIsNone(fc.alias)

        fc = FromClauseExpression(table="db.schema.table1", alias="A")
        self.assertEqual(fc.sql, "FROM db.schema.table1 AS A")
        self.assertListEqual(fc.tokens(), ['FROM', 'db.schema.table1', 'AS', 'A'])
        self.assertEqual(fc.alias, "A")

        fc = fc.join(table="db.schema.table2", alias="B", join_type="inner",
                     on=Equal(ColumnExpression("A.id"), ColumnExpression("B.id")))
        self.assertEqual(fc.sql, "FROM db.schema.table1 AS A INNER JOIN db.schema.table2 AS B ON A.id = B.id")
        self.assertListEqual(fc.tokens(), ['FROM', 'db.schema.table1', 'AS', 'A' ,'INNER JOIN' ,'db.schema.table2', 'AS', 'B', 'ON', 'A.id', '=', 'B.id'])
        self.assertIsNone(fc.alias)

    def test_from_clause_cross_join(self):
        fc = (
            FromClauseExpression(table="db.schema.table1", alias="A")
                .cross_join(table="db.schema.table1", alias="B")
        )
        self.assertEqual(fc.sql, "FROM db.schema.table1 AS A CROSS JOIN db.schema.table1 AS B")
        self.assertListEqual(fc.tokens(), ['FROM', 'db.schema.table1', 'AS', 'A', 'CROSS JOIN', 'db.schema.table1', 'AS', 'B'])


    def test_from_clause_duplicate_aliases(self):
        with self.assertRaises(TypeError) as cm:
            (
            FromClauseExpression(table="db.schema.table1", alias="A")
                .join(table="db.schema.table2", alias="A", join_type="inner", 
                      on=Equal(ColumnExpression("A.id"), ColumnExpression("A.id")))
            )
        self.assertEqual("duplicate aliases, 'A'", str(cm.exception))
            
        with self.assertRaises(TypeError) as cm:
            (
            FromClauseExpression(table="db.schema.table1", alias="A")
                .join(table="db.schema.table2", alias="B", join_type="inner", 
                      on=Equal(ColumnExpression("A.id"), ColumnExpression("B.id")))
                .join(table="db.schema.table2", alias="A", join_type="inner",
                      on=Equal(ColumnExpression("A.id"), ColumnExpression("B.id")))
            )
        self.assertTrue("can't have duplicate aliases for tables, found: " in str(cm.exception))

    def test_from_clause_sub_query(self):
        query = QueryExpression(
            from_clause=FromClauseExpression(table="db.schema.table1"),
            select_clause=SelectClauseExpression([ColumnExpression("a"), ColumnExpression("b")], [None, None])
            )
        # fails when there's no alias
        with self.assertRaises(TypeError) as cm:
            FromClauseExpression(query=query)
        self.assertEqual(str(cm.exception), "when calling with 1 key word argument, only 'table' and 'join_expression' are supported, got 'query'")

        fc = FromClauseExpression(query=query, alias="A")
        self.assertListEqual(fc.tokens(), ['FROM', '(', 'SELECT', 'a', ',', 'b', 'FROM', 'db.schema.table1', ')', 'AS', 'A'])


    def test_from_clause_bad_arguments(self):
        # 1 argument
        with self.assertRaises(TypeError) as cm:
            FromClauseExpression(tabl="foo")
        self.assertEqual("when calling with 1 key word argument, only 'table' and 'join_expression' are supported, got 'tabl'", str(cm.exception))

        # 2 arguments
        with self.assertRaises(TypeError) as cm:
            FromClauseExpression(table="foo", join_expression="bar")
        self.assertEqual("when calling with 2 key word arguments, either ('table', 'alias') or ('query', 'alias') are supported, got 'table' and 'join_expression'", str(cm.exception))

    def test_predicate_clause(self):
        where = WhereClauseExpression(Equal(ColumnExpression("t1.id"), ColumnExpression("t2.id")))
        self.assertEqual(where.sql, "WHERE t1.id = t2.id")
        self.assertListEqual(where.tokens(), ['WHERE', 't1.id', '=', 't2.id'])

        where = where.and_(Greater(ColumnExpression("t1.date"), ColumnExpression("t2.date")))
        self.assertEqual(where.sql, "WHERE ( t1.id = t2.id ) AND ( t1.date > t2.date )")
        self.assertListEqual(where.tokens(), ['WHERE', '(','t1.id', '=', 't2.id',')', 'AND', '(','t1.date', '>', 't2.date',')'])

        where = where.or_(Like(ColumnExpression("t1.foo"), LiteralExpression("%%bar")))
        self.assertEqual(where.sql, "WHERE ( ( t1.id = t2.id ) AND ( t1.date > t2.date ) ) OR ( t1.foo LIKE '%%bar' )")
        self.assertListEqual(where.tokens(), ["WHERE", "(","(","t1.id", "=", "t2.id",")", "AND", "(","t1.date", ">", "t2.date",")",")", "OR", "(","t1.foo", "LIKE" ,"'%%bar'",")"])

        having = HavingClauseExpression(Equal(ColumnExpression("t1.id"), ColumnExpression("t2.id")))
        self.assertEqual(having.sql, "HAVING t1.id = t2.id")
        self.assertListEqual(having.tokens(), ['HAVING', 't1.id', '=', 't2.id'])
        
        qualify = QualifyClauseExpression(Equal(ColumnExpression("t1.id"), ColumnExpression("t2.id")))
        self.assertEqual(qualify.sql, "QUALIFY t1.id = t2.id")
        self.assertListEqual(qualify.tokens(), ['QUALIFY', 't1.id', '=', 't2.id'])

    def test_group_by_clause_expressions(self):
        gb = GroupByClauseExpression(
            ColumnExpression("a"), 
            Plus(ColumnExpression("b"), LiteralExpression(2))
            )
        self.assertEqual(gb.sql, "GROUP BY a, b + 2")
        self.assertEqual(gb.tokens(), ['GROUP BY' ,'a',',', 'b', '+', '2'])

        with self.assertRaises(TypeError) as cm:
            GroupByClauseExpression(ColumnExpression("a"), 2)
        self.assertEqual(str(cm.exception),"expressions can only be list[int] or list[SelectableExpressionType]")

        with self.assertRaises(TypeError) as cm:
            GroupByClauseExpression(ColumnExpression("a"), ColumnExpression("a"))
        self.assertEqual(str(cm.exception),"got duplicates in grouping items")

    def test_order_by_spec_expression(self):
        obs = OrderBySpecExpression()
        self.assertEqual(obs.sql, "ASC NULLS FIRST")

        obs = OrderBySpecExpression(asc=False)
        self.assertEqual(obs.sql, "DESC NULLS FIRST")
        
        obs = OrderBySpecExpression(asc=False, nulls="LAST")
        self.assertEqual(obs.sql, "DESC NULLS LAST")

    def test_order_by_clause_assertions(self):

        with self.assertRaises(TypeError) as cm:
            OrderByClauseExpression(1, ColumnExpression("a"))
        self.assertEqual(str(cm.exception), "input must be a list with arguments that are either SelectableExpressionType or Tuple[SelectableExpressionType, OrderBySpecExpression]")

    def test_order_by_clause_expressions(self):
        ob = OrderByClauseExpression(
            ColumnExpression("a"), 
            (ColumnExpression("b"), OrderBySpecExpression(False))
            )
        self.assertEqual(ob.sql, "ORDER BY a ASC NULLS FIRST, b DESC NULLS FIRST")
        self.assertListEqual(ob.tokens(), ['ORDER BY', 'a', 'ASC NULLS FIRST', ',','b', 'DESC NULLS FIRST'])

        with self.assertRaises(TypeError) as cm:
            OrderByClauseExpression(
            ColumnExpression("a"), 
            (ColumnExpression("a"), OrderBySpecExpression(False))
            )
        self.assertEqual(str(cm.exception), "duplicate ordering items")

    def test_limit_clause(self):
        lc1 = LimitClauseExpression(100)
        lc2 = LimitClauseExpression(100, 50)
        self.assertEqual(lc1.sql, "LIMIT 100")
        self.assertEqual(lc2.sql, "LIMIT 100 OFFSET 50")