from unittest import TestCase

from sparkit.expression.base import *

class TestValidName(TestCase):

    def test_validname_sanity(self):
        inputs = ['aaa', 'a2a', '_aa']
        results = [ValidName(_) for _ in inputs]
        for i,r in zip(inputs, results):
            self.assertEqual(r.name, i)

    def test_validname_length(self):
        with self.assertRaises(TypeError) as cm:
            ValidName('')
        self.assertEqual("name cannot be an empty str", str(cm.exception))

    def test_validname_first_char(self):
        with self.assertRaises(TypeError) as cm:
            ValidName('2aa')
        expected = "illegal name, due to bad characters in these locations: [(0, '2')]"
        self.assertEqual(expected, str(cm.exception))

    def test_validname_other_chars(self):
        with self.assertRaises(TypeError) as cm:
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

    def test_validname_backticks(self):
        self.assertEqual(ValidName("`this is a backticked name`").name, "`this is a backticked name`")

class TestExpression(TestCase):

    def test_inheritance(self):
        self.assertTrue(isinstance(NullExpression(), NullExpression))
        self.assertTrue(isinstance(NullExpression(), Expression))

    def test_column_expression(self):
        col = ColumnExpression("a")
        self.assertEqual(col.name, col.sql)

    def test_column_expression_star(self):
        col = ColumnExpression("*")
        self.assertEqual(col.name, "*")
        self.assertEqual(col.tokens(), ["*"])

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

        self.assertEqual(bool_lit.tokens(), ["TRUE"])
        self.assertEqual(int_lit.tokens(), ["3245"])
        self.assertEqual(float_lit.tokens(), ["43.22"])
        self.assertEqual(float_lit2.tokens(), ["1000000.0"])
        self.assertEqual(str_lit.tokens(), ["'hello'"])