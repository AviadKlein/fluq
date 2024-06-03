from unittest import TestCase

from fluq.frame import *
from fluq.sql import lit, col, functions, table
from fluq.render import RenderingContextConfig

break_on_context_change = {
            'SELECT': RenderingContextConfig(break_on_change_context=True),
            'FROM': RenderingContextConfig(break_on_change_context=True),
            'GROUP BY': RenderingContextConfig(break_on_change_context=True),
            'ORDER BY': RenderingContextConfig(break_on_change_context=True),
            'LIMIT': RenderingContextConfig(break_on_change_context=True)
        }

class TestFrame(TestCase):
    
    def test_table_construction_method(self):
        frame = table("a")
        self.assertEqual(frame.sql, """SELECT * FROM a""")

    def test_call_method(self):
        frame = table("a")
        col: Column = frame("id")
        self.assertTrue(isinstance(col, Column))
        self.assertEqual(col.expr.sql, "a.id")

        frame = table("a").as_("t1")
        col = frame("id")
        self.assertTrue(isinstance(col, Column))
        self.assertEqual(col.expr.sql, "t1.id")
        
    def test_copy_doc(self):
        self.assertEqual(table("a").filter.__doc__.split('\n')[0], "An alias for 'where'")

    def test_alias(self):
        frame = table("a")
        self.assertEqual(frame.sql, """SELECT * FROM a""")
        # has automatic alias
        self.assertEqual(frame.alias, "a")

        frame = frame.as_("t1")

        # doesn't change the sql
        self.assertEqual(frame.sql, """SELECT * FROM a""")
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
        expected = 'SELECT a, b, c FROM t1'
        result = frame.sql
        self.assertEqual(expected, result)

        frame = frame.as_("B").select("a")
        result = frame.sql
        expected = 'SELECT a FROM ( SELECT a, b, c FROM t1 ) AS B'
        self.assertEqual(expected, result)

        frame = table("t1").select(
            (col("age") > 10).as_("above_10"),
            (col("gender") == lit("male")).as_("is_male"),
            )
        
        result = frame.sql
        expected = "SELECT age > 10 AS above_10, gender = 'male' AS is_male FROM t1"
        self.assertEqual(expected, result)

    def test_select_distinct(self):
        frame = table("t1").select("a", "b", "c").distinct()
        expected = 'SELECT DISTINCT a, b, c FROM t1'
        result = frame.sql
        self.assertEqual(expected, result)

    def test_select_distinct_from_set_operation(self):
        with self.assertRaises(SyntaxError) as cm:
            table("t1").union_all(table("t2")).distinct()
        self.assertEqual("querying over set operations requires an alias", str(cm.exception))

        query = table("t1").union_all(table("t2")).as_("t").distinct()
        self.assertEqual(query.sql, "SELECT DISTINCT * FROM ( SELECT * FROM t1 UNION ALL SELECT * FROM t2 ) AS t")

    def test_where(self):
        frame = table("t1").where((col("age") > 18) & (col("salary") < 50000)).select("id")
        result = frame.sql
        expected = 'SELECT id FROM t1 WHERE ( age > 18 ) AND ( salary < 50000 )'
        self.assertEqual(expected, result)

        # append a new condition
        frame = frame.where(col("address").is_not_null())
        result = frame.sql
        expected = 'SELECT id FROM t1 WHERE ( ( age > 18 ) AND ( salary < 50000 ) ) AND ( address IS NOT NULL )'
        self.assertEqual(expected, result)

    def test_join(self):
        t1 = table("db.schema.table1").as_("t1")
        t2 = table("db.schema.table2").as_("t2")
        inner = t1.join(t2, col("t1.id") == col("t2.id"))
        left = t1.join(t2, col("t1.id") == col("t2.id"), join_type='left')
        right = t1.join(t2, col("t1.id") == col("t2.id"), join_type='right')
        full_outer = t1.join(t2, col("t1.id") == col("t2.id"), join_type='full outer')

        expected_inner      = 'SELECT * FROM db.schema.table1 AS t1 INNER JOIN db.schema.table2 AS t2 ON t1.id = t2.id'
        expected_left       = 'SELECT * FROM db.schema.table1 AS t1 LEFT OUTER JOIN db.schema.table2 AS t2 ON t1.id = t2.id'
        expected_right      = 'SELECT * FROM db.schema.table1 AS t1 RIGHT OUTER JOIN db.schema.table2 AS t2 ON t1.id = t2.id'
        expected_full_outer = 'SELECT * FROM db.schema.table1 AS t1 FULL OUTER JOIN db.schema.table2 AS t2 ON t1.id = t2.id'

        self.assertEqual(inner.sql, expected_inner)
        self.assertEqual(left.sql, expected_left)
        self.assertEqual(right.sql, expected_right)
        self.assertEqual(full_outer.sql, expected_full_outer)

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
            'FROM (', 
            'SELECT t1.id, t2.salary', 
            'FROM db.schema.table1 AS t1 INNER JOIN db.schema.table2 AS t2 ON t1.id = t2.id ) AS a LEFT OUTER JOIN (', 
            'SELECT *', 
            'FROM db.schema.table3 ) AS t3 ON a.id = t3.id']
        result = left.sql(context2config=break_on_context_change).split('\n')
        print(result)
        self.assertListEqual(result, expected)
        
    def test_join_cartesian(self):
        t1 = table("db.schema.table1").as_("t1")
        t2 = table("db.schema.table2").as_("t2")
        result = t1.cartesian(t2)
        expected = [
            'SELECT *', 
            'FROM db.schema.table1 AS t1 CROSS JOIN db.schema.table2 AS t2']
        self.assertEqual(result.sql(context2config=break_on_context_change).split('\n'), expected)

        result = t1.cartesian(t2).select("t1.id", "t2.id")
        expected = [
            'SELECT t1.id, t2.id', 
            'FROM db.schema.table1 AS t1 CROSS JOIN db.schema.table2 AS t2']
        self.assertEqual(result.sql(context2config=break_on_context_change).split('\n'), expected)
        

    def test_group_by(self):
         result = (
             table("db.schema.payments").as_("t1")
             .group_by(col("customer_id"), col("date"))
             .agg(functions.sum(col("value")).as_("total_value"))
         )
         expected = [
             'SELECT customer_id, date, SUM( value ) AS total_value', 
             'FROM db.schema.payments', 
             'GROUP BY customer_id, date']
         self.assertListEqual(result.sql(context2config=break_on_context_change).split('\n'), expected)

    def test_order_by(self):
        result = (
             table("db.schema.payments").as_("t1")
             .select("id", "time", "value")
             .order_by("time")
         ).sql(context2config=break_on_context_change).split('\n')
        expected = [
            'SELECT id, time, value', 
            'FROM db.schema.payments', 
            'ORDER BY time ASC NULLS FIRST']
        self.assertListEqual(result, expected)

    def test_limit(self):
        result = (
            table("db.schema.payments").as_("t1")
             .select("id", "time", "value")
             .order_by("time")
             .limit(5)
        ).sql(context2config=break_on_context_change).split('\n')
        expected = [
            'SELECT id, time, value', 
            'FROM db.schema.payments', 
            'ORDER BY time ASC NULLS FIRST', 
            'LIMIT 5']
        self.assertListEqual(result, expected)

    def test_source_table_names(self):
        query = (
            table("t1").as_("t1").join(table("t2").as_("t2"), on=col("id1") == col("id2"), join_type='inner')
            .where(col("fk").is_in(table("t3").where(col("condition") == 1).select("id")))
        )
        result = query.source_table_names()
        for t in ['t1', 't2', 't3']:
            self.assertTrue(t in result)

    def test_frame_has_auto_alias_when_query_is_simple(self):
        q = table("db.t1").where(col("a") == col("b")).select("*")
        self.assertEqual(q.alias, "t1")
        
        
        

        


