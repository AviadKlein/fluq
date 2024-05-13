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
        expceted = "illegal name, due to bad characters in these locations: [(0, '2')]"
        self.assertEqual(expceted, str(cm.exception))

    def test_validname_other_chars(self):
        with self.assertRaises(Exception) as cm:
            ValidName('a;a')
        expceted = "illegal name, due to bad characters in these locations: [(1, ';')]"
        self.assertEqual(expceted, str(cm.exception))

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

    def test_literal_expression(self):
        bool_lit = Literal(True)
        int_lit = Literal(3245)
        float_lit = Literal(43.22)
        float_lit2 = Literal(1e6)
        str_lit = Literal("hello")

        self.assertEqual(bool_lit.sql, "TRUE")
        self.assertEqual(int_lit.sql, "3245")
        self.assertEqual(float_lit.sql, "43.22")
        self.assertEqual(float_lit2.sql, "1000000.0")
        self.assertEqual(str_lit.sql, "'hello'")

    def test_table_column_expression(self):
        self.fail("Not implemented")

    def test_logical_and_math_expressions(self):
        zipped = [
            (Equal(Literal(1), Literal("a")), "1 = 'a'"),
            (NotEqual(Literal(1), Literal("a")), "1 <> 'a'"),
            (Greater(Literal(1), Literal("a")), "1 > 'a'"),
            (GreaterOrEqual(Literal(1), Literal("a")), "1 >= 'a'"),
            (Less(Literal(1), Literal("a")), "1 < 'a'"),
            (LessOrEqual(Literal(1), Literal("a")), "1 <= 'a'"),
            (In(ColumnExpression("a"), 1, 2, 4.5, 55), "a IN (1, 2, 4.5, 55)"),
            (In(ColumnExpression("a"), True, False), "a IN (TRUE, FALSE)"),
            (In(ColumnExpression("a"), 'yo yo', 'ya ya', 'ye ye'), "a IN ('yo yo', 'ya ya', 'ye ye')"),
            (Not(ColumnExpression("a")), 'a <> TRUE'),
            (Not(Literal(False)), 'FALSE <> TRUE'),
            (IsNull(ColumnExpression("a")), 'a IS NULL'),
            (IsNotNull(ColumnExpression("a")), 'a IS NOT NULL'),
            (Between(ColumnExpression("a"), Literal(1), Literal(2)), 'a BETWEEN 1 AND 2'),
            (And(
                Equal(Literal(1), Literal("a")), 
                NotEqual(Literal(1), Literal("a"))
            ), "(1 = 'a') AND (1 <> 'a')"),
            (Or(Equal(Literal(1), Literal("a")), 
                NotEqual(Literal(1), Literal("a"))
            ), "(1 = 'a') OR (1 <> 'a')"),
            (Like(ColumnExpression("a"), Literal("%%abs")), "a LIKE '%%abs'"),
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
                .add(Equal(ColumnExpression("a"), Literal(1)), Literal("good"))
                .add(Equal(ColumnExpression("a"), Literal(0)), Literal("bad"))
        )

        expected = textwrap.dedent("""\
        CASE
        \tWHEN a = 1 THEN 'good'
        \tWHEN a = 0 THEN 'bad'
        END""")
        
        self.assertMultiLineEqual(case.sql, expected)


        case = (
            CaseExpression([])
                .add(Equal(ColumnExpression("a"), Literal(1)), Literal("good"))
                .add(Equal(ColumnExpression("a"), Literal(0)), Literal("bad"))
                .add_otherwise(Literal("dunno"))
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
            left_alias="a", right_alias="b")
