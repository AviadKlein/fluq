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

    def test_table_column_expression(self):
        self.fail("Not implemented")

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
        
        inner = InnerJoinOperationExpression(left=AnyExpression("t1"), right=AnyExpression("t2"))
        self.assertEqual(inner.sql, "t1 INNER JOIN t2")

        inner = InnerJoinOperationExpression(
            left=AnyExpression("t1"), 
            right=AnyExpression("t2"),
            left_alias="a")
        
        self.assertEqual(inner.sql, "t1 AS a INNER JOIN t2")

        left = LeftJoinOperationExpression(
            left=AnyExpression("t1"), 
            right=AnyExpression("t2"),
            left_alias="a", right_alias="b")
        
        self.assertEqual(left.sql, "t1 AS a LEFT OUTER JOIN t2 AS b")

        left_on = LeftJoinOperationExpression(
            left=AnyExpression("t1"), 
            right=AnyExpression("t2"),
            left_alias="a", right_alias="b", on=Equal(ColumnExpression("a.id"), ColumnExpression("b.id")))
        
        self.assertEqual(left_on.sql, "t1 AS a LEFT OUTER JOIN t2 AS b ON a.id = b.id")

    def test_join_nested(self):

        first = InnerJoinOperationExpression(
            left=AnyExpression("t1"), 
            right=AnyExpression("t2"),
            on=Equal(ColumnExpression("t1.id"), ColumnExpression("t2.id")))
        
        nested = InnerJoinOperationExpression(
            left=first,
            right=AnyExpression("t3"),
            on=Equal(ColumnExpression("t3.id"), ColumnExpression("t2.id")))
        

        self.assertEqual(nested.sql, "t1 INNER JOIN t2 ON t1.id = t2.id INNER JOIN t3 ON t3.id = t2.id")

    def test_cross_join_no_on_clause(self):

        cross = CrossJoinOperationExpression(
            left=AnyExpression("t1"), 
            right=AnyExpression("t2"),
            left_alias="A", right_alias="B"
        )

        self.assertEqual(cross.sql, "t1 AS A CROSS JOIN t2 AS B")
    
    def test_select_clause(self):
        select = SelectExpression.from_args(ColumnExpression("*"))
        self.assertEqual(select.sql, "SELECT *")

        select = select.add(ColumnExpression("t1"), "a")
        self.assertEqual(select.sql, "SELECT *, t1 AS a")
   
        with self.assertRaises(AssertionError) as cm:
            SelectExpression.from_args((ColumnExpression("*"), "A"))
        self.assertEqual(str(cm.exception), """ColumnExpression("*") can't have an alias, got 'A'""")

        with self.assertRaises(AssertionError) as cm:
             select = SelectExpression.from_args(ColumnExpression("*"))
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
        self.fail("TODO")

    def test_from_clause_duplicate_aliases(self):
        self.fail("TODO")

    def test_from_clause_bad_arguments(self):
        self.fail("TODO")

    def test_where_clause(self):
        self.fail("TODO")


        
        
