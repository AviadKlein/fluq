from unittest import TestCase

from sparkit.expression.base import *
from sparkit.expression.function import *
from sparkit.expression.selectable import ColumnExpression, LiteralExpression

class TestFunction(TestCase):

    def test_dynamic_functions(self):
        functions = SQLFunctionExpressions()

        self.assertTrue('FunctionExpressionMOD' in functions.__dir__())

        result = functions.FunctionExpressionMOD(X=LiteralExpression(5), Y=LiteralExpression(3))
        self.assertEqual(result.sql, "MOD(5, 3)")
        self.assertEqual(result.tokens(), ["MOD(5, 3)"])

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
        expected = ['CASE', 'WHEN', 'a', '=', '1', 'THEN', "'good'", 'WHEN', 'a', '=', '0', 'THEN', "'bad'", "END"]
        
        self.assertListEqual(case.tokens(), expected)

        case = (
            CaseExpression([])
                .add(Equal(ColumnExpression("a"), LiteralExpression(1)), LiteralExpression("good"))
                .add(Equal(ColumnExpression("a"), LiteralExpression(0)), LiteralExpression("bad"))
                .add_otherwise(LiteralExpression("dunno"))
        )

        expected = ['CASE', 'WHEN', 'a', '=', '1', 'THEN', "'good'", 'WHEN', 'a', '=', '0', 'THEN', "'bad'", "ELSE", "'dunno'", 'END']
        
        self.assertListEqual(case.tokens(), expected)