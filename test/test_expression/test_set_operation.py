from unittest import TestCase

from fluq.sql import table
from fluq.expression.set_operation import *
from fluq.render import RenderingContextConfig

break_on_context_change = {
            'SELECT': RenderingContextConfig(break_on_change_context=True),
            'FROM': RenderingContextConfig(break_on_change_context=True),
            'GROUP BY': RenderingContextConfig(break_on_change_context=True),
            'ORDER BY': RenderingContextConfig(break_on_change_context=True),
            'LIMIT': RenderingContextConfig(break_on_change_context=True)
        }

class TestSetOperation(TestCase):

    def test_union_all(self):
        a = table("a")
        b = table("b")
        union = a.union_all(b)
        result = union.sql(break_on_context_change).split('\n')
        expected = [
            'SELECT *', 
            'FROM a UNION ALL', 
            'SELECT *', 
            'FROM b']
        self.assertListEqual(result, expected)

    def test_union_distinct(self):
        a = table("a")
        b = table("b")
        union = a.union_distinct(b)
        result = union.sql(break_on_context_change).split('\n')
        expected = [
            'SELECT *', 
            'FROM a UNION DISTINCT', 
            'SELECT *', 
            'FROM b']
        self.assertListEqual(result, expected)

    def test_intersect(self):
        a = table("a")
        b = table("b")
        union = a.intersect_distinct(b)
        result = union.sql(break_on_context_change).split('\n')
        expected = [
            'SELECT *', 
            'FROM a INTERSECT DISTINCT', 
            'SELECT *', 
            'FROM b']
        self.assertListEqual(result, expected)

    def test_except(self):
        a = table("a")
        b = table("b")
        union = a.except_distinct(b)
        result = union.sql(break_on_context_change).split('\n')
        expected = [
            'SELECT *', 
            'FROM a EXCEPT DISTINCT', 
            'SELECT *', 
            'FROM b']
        self.assertListEqual(result, expected)

    def test_tokens_2_sets(self):
        a = table("a")
        b = table("b")
        result = a.union_all(b)._query_expr.tokens()
        expected = ['SELECT', '*', 'FROM', 'a', 'UNION ALL','SELECT', '*', 'FROM', 'b']
        self.assertListEqual(result, expected)
        
    def test_chained_set_operations(self):
        a = table("a")
        b = table("b")
        c = table("c")
        d = table("d")
        union = a.union_all(b).union_all(c).union_all(d)
        result = union._query_expr.tokens()
        expected = [
            'SELECT', '*', 
            'FROM', 'a',
            'UNION ALL', '(', 
            'SELECT', '*', 
            'FROM', 'b', 
            'UNION ALL', '(', 
            'SELECT', '*', 
            'FROM', 'c', 
            'UNION ALL', '(', 
            'SELECT', '*', 
            'FROM', 'd', ')', ')', ')']
        self.assertListEqual(result, expected)