from unittest import TestCase

from fluq.expression.base import *
from fluq.expression.function import *
from fluq.expression.selectable import ColumnExpression, LiteralExpression
from fluq.sql import col
from fluq.sql import functions as fn

class TestFunction(TestCase):

    def test_functions_params_arg_num_is_int(self):
        self.assertFalse(FunctionParams("MY_FUNC", 2).is_legit_number_of_args(0))
        self.assertTrue(FunctionParams("MY_FUNC", 2).is_legit_number_of_args(2))
        self.assertTrue(FunctionParams("MY_FUNC", 0).is_legit_number_of_args(0))

        with self.assertRaises(TypeError) as cm:
            FunctionParams("MY_FUNC", -2)
        self.assertEqual("can't have int smaller than 0", str(cm.exception))
        

    def test_functions_params_arg_num_is_none(self):
        logic = FunctionParams("MY_FUNC", None)
        self.assertTrue(logic.is_legit_number_of_args(2))
        self.assertTrue(logic.is_legit_number_of_args(200))
        self.assertTrue(logic.is_legit_number_of_args(0))

        with self.assertRaises(AssertionError) as cm:
            logic.is_legit_number_of_args(-1)

    def test_functions_params_arg_num_is_list(self):
        logic = FunctionParams("MY_FUNC", [2,5,6])
        self.assertTrue(logic.is_legit_number_of_args(2))
        self.assertTrue(logic.is_legit_number_of_args(5))
        self.assertTrue(logic.is_legit_number_of_args(6))
        self.assertFalse(logic.is_legit_number_of_args(7))

    def test_functions_params_arg_num_is_list_with_none(self):
        with self.assertRaises(TypeError) as cm:
            FunctionParams("F", [None, None])
        self.assertEqual("can't have more than 1 None in arg_num", str(cm.exception))

        with self.assertRaises(TypeError) as cm:
            FunctionParams("F", [None, 1, 2])
        self.assertEqual("when passing [None, ...] to arg_num, there can be only 1 more int", str(cm.exception))

        self.assertTrue(FunctionParams("F", [None, 1]).is_legit_number_of_args(1))
        self.assertTrue(FunctionParams("F", [None, 1]).is_legit_number_of_args(2))
        self.assertTrue(FunctionParams("F", [None, 1]).is_legit_number_of_args(200))

        self.assertFalse(FunctionParams("F", [None, 3]).is_legit_number_of_args(2))
        
    def test_function_params_dynamic_creation(self):
        fp = FunctionParams("F", 2)
        f = fp.to_expression(False)(LiteralExpression(1), LiteralExpression(2))
        self.assertEqual(str(type(f)), "<class 'abc.DynamicFunctionExpressionF'>")
        self.assertListEqual(f.tokens(), ['F(', '1', ',', '2', ')'])

    def test_all_functions_are_rendered(self):
        expected_classes = []
        for params in SQLFunctionsGenerator._params():
            expected_classes.append(params.clazz_name(False))
            if params.supports_distinct:
                expected_classes.append(params.clazz_name(True))
        
        actual_classes = [_ for _ in SQLFunctionsGenerator().__dir__() if FunctionParams.clazz_prefix() in _]
        self.assertEqual(len(actual_classes), len(expected_classes))
        self.assertEqual(len(set(actual_classes)), len(set(expected_classes)))
        
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

    def test_functions(self):
        print(type(fn.sum(col("a"))))
        print(type(fn.sum(col("income")).as_("sum_income")))