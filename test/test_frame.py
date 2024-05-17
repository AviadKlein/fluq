from unittest import TestCase

from frame import *
from sql import lit, col

class TestFrame(TestCase):
    
    def test_table_construction_method(self):
        frame = table("a")
        self.assertEqual(frame.sql, """SELECT *\nFROM a""")
        
    def test_copy_doc(self):
        self.assertEqual(table("a").filter.__doc__.split('\n')[0], "An alias for 'where'")

    def test_alias(self):
        frame = table("a")
        self.assertEqual(frame.sql, """SELECT *\nFROM a""")
        # has no alias
        self.assertIsNone(frame.alias)

        frame = frame.as_("t1")

        # doesn't change the sql
        self.assertEqual(frame.sql, """SELECT *\nFROM a""")
        # but has an alias
        self.assertEqual(frame.alias, "t1")

    def test_alias_bad_name(self):
        with self.assertRaises(Exception) as cm:
            table("a").as_("23abs")
        self.assertTrue("illegal name, due to bad characters in these locations" in str(cm.exception))

    def test_alias_setter(self):
        with self.assertRaises(SyntaxError) as cm:
            frame = table("a").as_("t1")   
            frame.alias = "t2"
        self.assertEqual("can't assign alias, use the as_ method instead", str(cm.exception))

    def test_is_select_all(self):
        frame = table("a")
        self.assertTrue(frame._is_select_all())

        frame = frame.select("*")
        self.assertTrue(frame._is_select_all())

        frame = table("a").select("a", "b", "c")
        self.assertFalse(frame._is_select_all())

    def test_select(self):
        frame = table("t1").select("a", "b", "c")
        expected = ['SELECT a, b, c', 'FROM t1']
        result = frame.sql.split('\n')
        self.assertListEqual(expected, result)

        with self.assertRaises(AssertionError) as cm:
            frame.select("a")
        self.assertEqual("when sub selecting, first use an alias", str(cm.exception))

        frame = frame.as_("B").select("a")
        result = frame.sql.split('\n')
        expected = [
            'SELECT a',
            'FROM (SELECT a, b, c',
            'FROM t1) AS B'
            ]
        self.assertListEqual(expected, result)

        frame = table("t1").select(
            (col("age") > 10).as_("above_10"),
            (col("gender") == lit("male")).as_("is_male"),
            )
        
        result = frame.sql.split('\n')
        expected = [
            "SELECT age > 10 AS above_10, gender = 'male' AS is_male",
            "FROM t1"
        ]
        self.assertListEqual(expected, result)

    def test_where(self):
        frame = table("t1").where((col("age") > 18) & (col("salary") < 50000)).select("id")
        result = frame.sql.split('\n')
        expected = [
            'SELECT id', 
            'FROM t1', 
            'WHERE (age > 18) AND (salary < 50000)']
        self.assertListEqual(expected, result)

        # append a new condition
        frame = frame.where(col("address").is_not_null())
        result = frame.sql.split('\n')
        expected = [
            'SELECT id', 
            'FROM t1', 
            'WHERE ((age > 18) AND (salary < 50000)) AND (address IS NOT NULL)']
        self.assertListEqual(expected, result)

    def test_join(self):
        t1 = table("db.schema.table1").as_("t1")
        t2 = table("db.schema.table2").as_("t2")
        inner = t1.join(t2, col("t1.id") == col("t2.id"))
        left = t1.join(t2, col("t1.id") == col("t2.id"), join_type='left')
        right = t1.join(t2, col("t1.id") == col("t2.id"), join_type='right')
        full_outer = t1.join(t2, col("t1.id") == col("t2.id"), join_type='full outer')

        expected_inner      = ['SELECT *', 'FROM db.schema.table1 AS t1 INNER JOIN db.schema.table2 AS t2 ON t1.id = t2.id']
        expected_left       = ['SELECT *', 'FROM db.schema.table1 AS t1 LEFT OUTER JOIN db.schema.table2 AS t2 ON t1.id = t2.id']
        expected_right      = ['SELECT *', 'FROM db.schema.table1 AS t1 RIGHT OUTER JOIN db.schema.table2 AS t2 ON t1.id = t2.id']
        expected_full_outer = ['SELECT *', 'FROM db.schema.table1 AS t1 FULL OUTER JOIN db.schema.table2 AS t2 ON t1.id = t2.id']

        self.assertEqual(inner.sql.split('\n'), expected_inner)
        self.assertEqual(left.sql.split('\n'), expected_left)
        self.assertEqual(right.sql.split('\n'), expected_right)
        self.assertEqual(full_outer.sql.split('\n'), expected_full_outer)

    def test_join_nested(self):
        t1 = table("db.schema.table1").as_("t1")
        t2 = table("db.schema.table2").as_("t2")
        inner = t1.join(t2, col("t1.id") == col("t2.id")).select("t1.id", "t2.salary")
        left = (
            inner.as_("a").
            join(
                other=table("db.schema.table3").as_("t3"), 
                on=col("a.id")==col("t3.id"),
                join_type='left'
                )
            .select("a.id", "t3.age", "a.salary")
            )
        expected = [
            'SELECT a.id, t3.age, a.salary', 
            'FROM (SELECT t1.id, t2.salary', 
            'FROM db.schema.table1 AS t1 INNER JOIN db.schema.table2 AS t2 ON t1.id = t2.id) AS a LEFT OUTER JOIN (SELECT *', 
            'FROM db.schema.table3) AS t3 ON a.id = t3.id']
        result = left.sql.split('\n')
        self.assertListEqual(result, expected)
        
    
    def test_group_by(self):
        self.fail("Not Implemented")

        


