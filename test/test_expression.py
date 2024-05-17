from __future__ import annotations
from unittest import TestCase
import textwrap

from expression import *

class TestIndent(TestCase):

    def test_indent(self):
        indent = Indent(3, 'a')
        self.assertEqual(indent.render(), 'aaa')
        self.assertEqual(indent.plus1().render(), 'aaaa')
        self.assertEqual(indent.plus1().plus1().render(), 'aaaaa')

        self.assertEqual(f"start{Indent(0)}stop", "startstop")
        self.assertEqual(f"start{Indent(1)}stop", "start\tstop")

class TestValidName(TestCase):

    def test_validname_sanity(self):
        inputs = ['aaa', 'a2a', '_aa']
        results = [ValidName(_) for _ in inputs]
        for i,r in zip(inputs, results):
            self.assertEqual(r.name, i)

    def test_validname_length(self):
        with self.assertRaises(AssertionError) as cm:
            ValidName('')
        self.assertEqual("name cannot be an empty str", str(cm.exception))

    def test_validname_first_char(self):
        with self.assertRaises(Exception) as cm:
            ValidName('2aa')
        expected = "illegal name, due to bad characters in these locations: [(0, '2')]"
        self.assertEqual(expected, str(cm.exception))

    def test_validname_other_chars(self):
        with self.assertRaises(Exception) as cm:
            ValidName('a;a')
        expected = "illegal name, due to bad characters in these locations: [(1, ';')]"
        self.assertEqual(expected, str(cm.exception))

    def test_validname_last_char_is_dot(self):
        with self.assertRaises(Exception) as cm:
            ValidName('a.')
        expected = "illegal name, due to bad characters in these locations: [(1, '.')]"
        self.assertEqual(expected, str(cm.exception))

    def test_validname_dots(self):
        self.assertEqual(ValidName("a.b.c").name, "a.b.c")
        self.assertEqual(ValidName("a....b..c").name, "a.b.c")

class TestExpression(TestCase):

    def test_inheritance(self):
        self.assertTrue(isinstance(NullExpression(), NullExpression))
        self.assertTrue(isinstance(NullExpression(), Expression))

    def test_column_expression(self):
        col = ColumnExpression("a")
        self.assertEqual(col.name, col.sql)

        self.assertEqual(col.to_logical().sql, "a IS NOT NULL")

    def test_column_expression_star(self):
        col = ColumnExpression("*")
        self.assertEqual(col.name, "*")

    def test_column_expression_star_equals(self):
        c1 = ColumnExpression("*")
        c2 = ColumnExpression("*")
        c3 = AnyExpression("*")
        c4 = AnyExpression("*")
        self.assertEqual(c1, c2)
        self.assertNotEqual(c1, c3)
        self.assertEqual(c3, c4)



    def test_literal_expression(self):
        bool_lit = LiteralExpression(True)
        int_lit = LiteralExpression(3245)
        float_lit = LiteralExpression(43.22)
        float_lit2 = LiteralExpression(1e6)
        str_lit = LiteralExpression("hello")

        self.assertEqual(bool_lit.sql, "TRUE")
        self.assertEqual(int_lit.sql, "3245")
        self.assertEqual(float_lit.sql, "43.22")
        self.assertEqual(float_lit2.sql, "1000000.0")
        self.assertEqual(str_lit.sql, "'hello'")

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


    def test_empty_case_expression(self):
        case = CaseExpression([])

        self.assertIsNone(case.otherwise)
        self.assertEqual(len(list(case.cases)), 0)

        with self.assertRaises(ValueError) as cm:
            case.sql
        
        self.assertEqual("can't render to sql with 0 cases", str(cm.exception))

    def test_case_expression(self):
        case = (
            CaseExpression([])
                .add(Equal(ColumnExpression("a"), LiteralExpression(1)), LiteralExpression("good"))
                .add(Equal(ColumnExpression("a"), LiteralExpression(0)), LiteralExpression("bad"))
        )

        expected = textwrap.dedent("""\
        CASE
        \tWHEN a = 1 THEN 'good'
        \tWHEN a = 0 THEN 'bad'
        END""")
        
        self.assertMultiLineEqual(case.sql, expected)


        case = (
            CaseExpression([])
                .add(Equal(ColumnExpression("a"), LiteralExpression(1)), LiteralExpression("good"))
                .add(Equal(ColumnExpression("a"), LiteralExpression(0)), LiteralExpression("bad"))
                .add_otherwise(LiteralExpression("dunno"))
        )

        expected = textwrap.dedent("""\
        CASE
        \tWHEN a = 1 THEN 'good'
        \tWHEN a = 0 THEN 'bad'
        \tELSE 'dunno'
        END""")
        
        self.assertMultiLineEqual(case.sql, expected)

    def test_join_operation(self):
        
        inner = InnerJoinOperationExpression(left=TableNameExpression("t1"), right=TableNameExpression("t2"))
        self.assertEqual(inner.sql, "t1 INNER JOIN t2")

        inner = InnerJoinOperationExpression(
            left=TableNameExpression("t1"), 
            right=TableNameExpression("t2"),
            left_alias="a")
        
        self.assertEqual(inner.sql, "t1 AS a INNER JOIN t2")

        left = LeftJoinOperationExpression(
            left=TableNameExpression("t1"), 
            right=TableNameExpression("t2"),
            left_alias="a", right_alias="b")
        
        self.assertEqual(left.sql, "t1 AS a LEFT OUTER JOIN t2 AS b")

        left_on = LeftJoinOperationExpression(
            left=TableNameExpression("t1"), 
            right=TableNameExpression("t2"),
            left_alias="a", right_alias="b", on=Equal(ColumnExpression("a.id"), ColumnExpression("b.id")))
        
        self.assertEqual(left_on.sql, "t1 AS a LEFT OUTER JOIN t2 AS b ON a.id = b.id")

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

    def test_join_subquery(self):
        query = QueryExpression(
            from_clause=FromClauseExpression(table="db.schema.table1"),
            select_clause=SelectClauseExpression([ColumnExpression("a"), ColumnExpression("b")], [None, None])
            )
        inner = InnerJoinOperationExpression(left=query, right=TableNameExpression("t2"), left_alias="A", 
                                             on=Equal(ColumnExpression("A.a"), ColumnExpression("t2.a")))
        expected = "(SELECT a, b\nFROM db.schema.table1) AS A INNER JOIN t2 ON A.a = t2.a"
        self.assertEqual(inner.sql, expected)

    def test_cross_join_no_on_clause(self):

        cross = CrossJoinOperationExpression(
            left=TableNameExpression("t1"), 
            right=TableNameExpression("t2"),
            left_alias="A", right_alias="B"
        )

        self.assertEqual(cross.sql, "t1 AS A CROSS JOIN t2 AS B")
    
    def test_select_clause(self):
        select = SelectClauseExpression.from_args(ColumnExpression("*"))
        self.assertEqual(select.sql, "SELECT *")

        select = select.add(ColumnExpression("t1"), "a")
        self.assertEqual(select.sql, "SELECT *, t1 AS a")
   
        with self.assertRaises(AssertionError) as cm:
            SelectClauseExpression.from_args((ColumnExpression("*"), "A"))
        self.assertEqual(str(cm.exception), """ColumnExpression("*") can't have an alias, got 'A'""")

        with self.assertRaises(AssertionError) as cm:
             select = SelectClauseExpression.from_args(ColumnExpression("*"))
             select.add(ColumnExpression("*"))
        self.assertEqual(str(cm.exception), """can only have 1 ColumnExpression("*")""")

    def test_from_clause(self):
        fc = FromClauseExpression(table="db.schema.table1")
        self.assertEqual(fc.sql, "FROM db.schema.table1")
        self.assertIsNone(fc.alias)

        fc = FromClauseExpression(table="db.schema.table1", alias="A")
        self.assertEqual(fc.sql, "FROM db.schema.table1 AS A")
        self.assertEqual(fc.alias, "A")

        fc = fc.join(table="db.schema.table2", alias="B", join_type="inner",
                     on=Equal(ColumnExpression("A.id"), ColumnExpression("B.id")))
        self.assertEqual(fc.sql, "FROM db.schema.table1 AS A INNER JOIN db.schema.table2 AS B ON A.id = B.id")
        self.assertIsNone(fc.alias)

    def test_from_clause_cross_join(self):
        fc = (
            FromClauseExpression(table="db.schema.table1", alias="A")
                .cross_join(table="db.schema.table1", alias="B")
        )
        self.assertEqual(fc.sql, "FROM db.schema.table1 AS A CROSS JOIN db.schema.table1 AS B")


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
        expected = "FROM (SELECT a, b\nFROM db.schema.table1) AS A"
        self.assertEqual(expected, fc.sql)


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

        where = where.and_(Greater(ColumnExpression("t1.date"), ColumnExpression("t2.date")))
        self.assertEqual(where.sql, "WHERE (t1.id = t2.id) AND (t1.date > t2.date)")

        where = where.or_(Like(ColumnExpression("t1.foo"), LiteralExpression("%%bar")))
        self.assertEqual(where.sql, "WHERE ((t1.id = t2.id) AND (t1.date > t2.date)) OR (t1.foo LIKE '%%bar')")

        having = HavingClauseExpression(Equal(ColumnExpression("t1.id"), ColumnExpression("t2.id")))
        self.assertEqual(having.sql, "HAVING t1.id = t2.id")
        
        qualify = QualifyClauseExpression(Equal(ColumnExpression("t1.id"), ColumnExpression("t2.id")))
        self.assertEqual(qualify.sql, "QUALIFY t1.id = t2.id")

    def test_group_by_clause_positional(self):
        gb = GroupByClauseExpression(1,3,6,7)
        self.assertEqual(gb.sql, "GROUP BY 1, 3, 6, 7")

        gb = GroupByClauseExpression(5,2,1)
        self.assertEqual(gb.sql, "GROUP BY 5, 2, 1")

        with self.assertRaises(TypeError) as cm:
            GroupByClauseExpression(0)
        self.assertEqual("can't have non-positive positional grouping items", str(cm.exception))

        with self.assertRaises(TypeError) as cm:
            GroupByClauseExpression(2,2)
        self.assertEqual("got duplicates in grouping items", str(cm.exception))

    def test_group_by_clause_expressions(self):
        gb = GroupByClauseExpression(
            ColumnExpression("a"), 
            Plus(ColumnExpression("b"), LiteralExpression(2))
            )
        self.assertEqual(gb.sql, "GROUP BY a, b + 2")

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

    def test_order_by_clause_positional(self):
        ob = OrderByClauseExpression(1,2,3)
        self.assertEqual(ob.sql, "ORDER BY 1, 2, 3")

        with self.assertRaises(TypeError) as cm:
            OrderByClauseExpression(1, ColumnExpression("a"))
        self.assertEqual(str(cm.exception), "input can be either list of ints or a list with arguments that are either SelectableExpressionType or Tuple[SelectableExpressionType, OrderBySpecExpression]")
    
        with self.assertRaises(TypeError) as cm:
            OrderByClauseExpression(0)
        self.assertEqual(str(cm.exception), "can't have non-positive positional ordering items")

        with self.assertRaises(TypeError) as cm:
            OrderByClauseExpression(1, 1)
        self.assertEqual(str(cm.exception), "duplicate ordering items")

    def test_order_by_clause_expressions(self):
        ob = OrderByClauseExpression(
            ColumnExpression("a"), 
            (ColumnExpression("b"), OrderBySpecExpression(False))
            )
        self.assertEqual(ob.sql, "ORDER BY a ASC NULLS FIRST, b DESC NULLS FIRST")

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

    def test_query_expression(self):
        query = QueryExpression(
            from_clause=FromClauseExpression(table="db.schema.table1"),
            select_clause=SelectClauseExpression([ColumnExpression("a"), ColumnExpression("b")], [None, None])
            )
        expected = """SELECT a, b\nFROM db.schema.table1"""
        self.assertEqual(query.sql, expected)



        

    

        
        
