from unittest import TestCase

from sparkit.sql import table

class TestSetOperation(TestCase):

    def test_union_all(self):
        a = table("a")
        b = table("b")
        union = a.union_all(b)
        result = union.sql.split('\n')
        expected = ['SELECT *', 'FROM a', 'UNION ALL', 'SELECT *', 'FROM b']
        self.assertListEqual(result, expected)

    def test_union_distinct(self):
        a = table("a")
        b = table("b")
        union = a.union_distinct(b)
        result = union.sql.split('\n')
        expected = ['SELECT *', 'FROM a', 'UNION DISTINCT', 'SELECT *', 'FROM b']
        self.assertListEqual(result, expected)

    def test_intersect(self):
        a = table("a")
        b = table("b")
        union = a.intersect_distinct(b)
        result = union.sql.split('\n')
        expected = ['SELECT *', 'FROM a', 'INTERSECT DISTINCT', 'SELECT *', 'FROM b']
        self.assertListEqual(result, expected)

    def test_except(self):
        a = table("a")
        b = table("b")
        union = a.except_distinct(b)
        result = union.sql.split('\n')
        expected = ['SELECT *', 'FROM a', 'EXCEPT DISTINCT', 'SELECT *', 'FROM b']
        self.assertListEqual(result, expected)

    def test_chained_set_operations(self):
        a = table("a")
        b = table("b")
        c = table("c")
        d = table("d")
        union = a.union_all(b).union_all(c).union_all(d)
        result = union.sql.split('\n')
        print(result)
        expected = [
            'SELECT *', 
            'FROM a',
            'UNION ALL (', 
            'SELECT *', 
            'FROM b', 
            'UNION ALL (', 
            'SELECT *', 
            'FROM c', 
            'UNION ALL', 
            'SELECT *', 
            'FROM d))']
        self.assertListEqual(result, expected)