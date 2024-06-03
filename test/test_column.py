from unittest import TestCase

from fluq.column import *
from fluq.expression.literals import OrderBySpecExpression
from fluq.expression.selectable import ColumnExpression, LiteralExpression, NegatedExpression
from fluq.sql import *


class TestColumn(TestCase):

    def test_init(self):
        c = col("a")
        print(c.expr.sql)
        self.assertEqual(c.expr.sql, "a")
        self.assertIsNone(c.alias)
        self.assertTrue(isinstance(c.expr, ColumnExpression))

        c = Column(name="a")
        self.assertEqual(c.expr.sql, "a")
        self.assertIsNone(c.alias)
        self.assertTrue(isinstance(c.expr, ColumnExpression))

        c = Column(name="a", alias="b")
        self.assertEqual(c.expr.sql, "a")
        self.assertEqual(c.alias, "b")
        self.assertTrue(isinstance(c.expr, ColumnExpression))

        c = Column(expression=LiteralExpression(3))
        self.assertEqual(c.expr.sql, "3")
        self.assertIsNone(c.alias)
        self.assertTrue(isinstance(c.expr, LiteralExpression))

        c = Column(expression=LiteralExpression(3), alias="id")
        self.assertEqual(c.expr.sql, "3")
        self.assertEqual(c.alias, "id")
        self.assertTrue(isinstance(c.expr, LiteralExpression))

        c = lit(3).as_("id")
        self.assertEqual(c.expr.sql, "3")
        self.assertEqual(c.alias, "id")
        self.assertTrue(isinstance(c.expr, LiteralExpression))

    def test_logicals(self):

        a = col("a")
        b = col("b")
        result: Column = a == b
        self.assertTrue(isinstance(result, Column))
        self.assertTrue(isinstance(result.expr, Equal))
        self.assertEqual(result.expr.sql, "a = b")

        result: Column = a == 1
        self.assertTrue(isinstance(result, Column))
        self.assertEqual(result.expr.sql, "a = 1")
        self.assertEqual(result.expr.right, LiteralExpression(1))

        result: Column = a != b
        self.assertTrue(isinstance(result.expr, NotEqual))
        self.assertEqual(result.expr.sql, "a <> b")

        self.assertEqual((a > b).expr.sql, "a > b")
        self.assertEqual((a > lit(1)).expr.sql, "a > 1")
        self.assertEqual((a > 1).expr.sql, "a > 1")

        self.assertEqual((a >= b).expr.sql, "a >= b")
        self.assertEqual((a >= 0).expr.sql, "a >= 0")

        self.assertEqual((a < b).expr.sql, "a < b")
        self.assertEqual((a < -10).expr.sql, "a < -10")
        
        self.assertEqual((a <= b).expr.sql, "a <= b")
        self.assertEqual((a <= 1e3).expr.sql, "a <= 1000.0")
        self.assertEqual((a <= 10_000).expr.sql, "a <= 10000")

        self.assertEqual(a.is_not_null().expr.sql, "a IS NOT NULL")
        self.assertEqual(a.is_null().expr.sql, "a IS NULL")

        self.assertEqual(a.between(2, 3).expr.sql, "a BETWEEN 2 AND 3")
        self.assertEqual(a.between(lit(2), lit(3)).expr.sql, "a BETWEEN 2 AND 3")

        self.assertEqual(((a <= b) & (b < 5)).expr.sql, "( a <= b ) AND ( b < 5 )")
        self.assertEqual(((a <= b) | (b < 5)).expr.sql, "( a <= b ) OR ( b < 5 )")

        self.assertEqual(a.like("%%foobar").expr.sql, "a LIKE '%%foobar'")

    def test_like_quantifier(self):
        a = col("a").like_all(array("%%foobar", "%%ity"))
    
        print(a.expr.sql)

    def test_math(self):

        a = col("a")
        b = col("b")

        # unary negation
        self.assertEqual((-a).expr.sql, "-a")
        self.assertTrue(isinstance(-a, Column))
        self.assertTrue(isinstance((-a).expr, NegatedExpression))

        # arithmetic
        self.assertEqual((a + b).expr.sql, "a + b")
        self.assertEqual((a - b).expr.sql, "a - b")
        self.assertEqual((a * b).expr.sql, "a * b")
        self.assertEqual((a / b).expr.sql, "a / b")
        self.assertEqual((a // b).expr.sql, "FLOOR( a / b )")
        self.assertEqual((a % b).expr.sql, "MOD( a, b )")
        self.assertEqual(abs(a).expr.sql, "ABS( a )")
        self.assertEqual((a**3).expr.sql, "POWER( a, 3 )")
    

    def test_case_expr(self):

        # case expressions
        case_ = when(col("a") > 5, 0).when(col("a") > 100, 1).otherwise(-1)
        expr: CaseExpression = case_.expr

        expected = [
            'WHEN', 'a', '>', '5', 'THEN', '0',
            'WHEN', 'a', '>', '100', 'THEN', '1',
            'ELSE', '-1'
        ]
        result = expr.case_tokens()
        self.assertListEqual(expected, result)

    def test_functions(self):
        
        result = functions.mod(col("a"), col("b"))
        self.assertEqual(result.expr.sql, "MOD( a, b )")

        result = functions.floor(lit(1.2))
        self.assertEqual(result.expr.sql, "FLOOR( 1.2 )")

        result = functions.current_date()
        self.assertEqual(result.expr.sql, "CURRENT_DATE( )")

        result = functions.sum(col("a"))
        self.assertEqual(result.expr.sql, "SUM( a )")

        result = functions.sum(col("a"))
        self.assertEqual(result.expr.sql, "SUM( a )")

    def test_ordering(self):
        
        c = col("a")
        self.assertTrue(c.order_by_spec.asc)
        self.assertEqual(c.order_by_spec.nulls, "FIRST")

        c = col("a").asc(nulls="LAST")
        self.assertTrue(c.order_by_spec.asc)
        self.assertEqual(c.order_by_spec.nulls, "LAST")

        c = col("a").desc()
        self.assertFalse(c.order_by_spec.asc)
        self.assertEqual(c.order_by_spec.nulls, "FIRST")

        c = col("a").desc(nulls="LAST")
        self.assertFalse(c.order_by_spec.asc)
        self.assertEqual(c.order_by_spec.nulls, "LAST")

        # keeps nulls spec when changing order
        c = Column(
            expression=ColumnExpression("a"), 
            alias="a", 
            order_by_spec=OrderBySpecExpression(asc=True, nulls="LAST")
            )
        c = c.desc()
        self.assertEqual(c.order_by_spec.nulls, "LAST")

    def test_window_spec(self):
        ws = WindowSpec() # empty init
        result = ws._to_expr().tokens()
        self.assertEqual(result, [])

        ws = WindowSpec().partition_by("a", "b")
        result = ws._to_expr().tokens()
        self.assertEqual(result, ['PARTITION BY', 'a', 'b'])
        

        ws = WindowSpec().partition_by(col("a"), col("b"))
        result = ws._to_expr().tokens()
        self.assertEqual(result, ['PARTITION BY' ,'a', 'b'])

        ws = WindowSpec().partition_by(col("a"), col("b")).order_by("a")
        result = ws._to_expr().tokens()
        print(result)
        self.assertEqual(result, ['PARTITION BY', 'a', 'b', 'ORDER BY', 'a', 'ASC NULLS FIRST'])

        ws = WindowSpec().partition_by(col("a"), col("b")).order_by(col("a").desc(nulls="last"))
        result = ws._to_expr().tokens()
        self.assertEqual(result, ['PARTITION BY', 'a', 'b', 'ORDER BY', 'a', 'DESC NULLS LAST'])

        ws = (
            WindowSpec().partition_by(col("a"), col("b"))
            .order_by(col("a").desc(nulls="last")).rows_between(None, 0)
            )
        
        result = ws._to_expr().tokens()
        expected = ['PARTITION BY', 'a', 'b', 'ORDER BY', 'a' ,'DESC NULLS LAST', 'ROWS', 'BETWEEN', 'UNBOUNDED PRECEDING', 'AND', 'CURRENT ROW']
        self.assertListEqual(result, expected)

    def test_window_spec_syntax_error_when_no_order_by_defined(self):
        with self.assertRaises(SyntaxError) as cm:
            WindowSpec().partition_by("player").rows_between(-5,5)._to_expr()
        self.assertEqual(
            str(cm.exception), 
            "If a WindowFrameExpression is defined in a WindowSpecExpression, and order_by object needs to be defined as well"
            )

    def test_frame_example_with_window_spec(self):
        # SQL example
        t = (
            table("db.schema.payments").as_("p")
            .group_by(col("player"), col("date"))
            .agg(
                functions.sum(col("value")).as_("sum_value"),
                functions.sum(col("value")).over(WindowSpec().partition_by("player")).as_("total_per_player"),
                functions.sum(col("value")).over(WindowSpec().partition_by("player").order_by("date").rows_between(-5,5)).as_("running_window")
                )
        )
        result = t.sql
        expected = """SELECT player, date, SUM( value ) AS sum_value, SUM( value ) OVER ( PARTITION BY player ) AS total_per_player, SUM( value ) OVER ( PARTITION BY player ORDER BY date ASC NULLS FIRST ROWS BETWEEN 5 PRECEDING AND 5 FOLLOWING ) AS running_window FROM db.schema.payments GROUP BY player, date"""
        self.assertEqual(result, expected)
        
        result = t._query_expr.tokens()
        expected = ['SELECT', 'player', ',', 'date', ',', 'SUM(', 'value', ')', 'AS' ,'sum_value', ',', 'SUM(', 'value', ')', 'OVER', '(', 'PARTITION BY', 'player',')', 'AS', 'total_per_player', ',', 'SUM(', 'value' ,')', 'OVER','(','PARTITION BY', 'player',
                    'ORDER BY', 'date', 'ASC NULLS FIRST', 'ROWS', 'BETWEEN', '5 PRECEDING', 'AND', '5 FOLLOWING',')', 'AS', 'running_window', 
                    'FROM', 'db.schema.payments', 
                    'GROUP BY', 'player', ',', 'date']
        self.assertListEqual(result, expected)

    def test_interval(self):
        t = table("db.schema.table").select(interval(3).DAY)
        print(t.sql)
    
    def test_position_keyword(self):
        self.assertEqual(PositionKeyword(3).symbol(), "PositionKeyword")
        self.assertEqual(OFFSET(3).symbol(), "OFFSET")

    def test_simple_array_indexing(self):
        t = table("db.schema.table").select(col("some_array")[0].as_("first_value"))
        self.assertEqual(t.sql, "SELECT some_array[ 0 ] AS first_value FROM db.schema.table")

    def test_ordinal_array_indexing(self):
        t = table("db.schema.table").select(col("some_array")[ORDINAL(3)].as_("fourth_value"))
        self.assertEqual(t.sql, "SELECT some_array[ ORDINAL(3) ] AS fourth_value FROM db.schema.table")

        t = table("db.schema.table").select(col("some_array")[SAFE_ORDINAL(3)].as_("fourth_value"))
        self.assertEqual(t.sql, "SELECT some_array[ SAFE_ORDINAL(3) ] AS fourth_value FROM db.schema.table")

    def test_offset_array_indexing(self):
        t = table("db.schema.table").select(col("some_array")[OFFSET(3)].as_("third"))
        self.assertEqual(t.sql, "SELECT some_array[ OFFSET(3) ] AS third FROM db.schema.table")

        t = table("db.schema.table").select(col("some_array")[SAFE_OFFSET(3)].as_("third"))
        self.assertEqual(t.sql, "SELECT some_array[ SAFE_OFFSET(3) ] AS third FROM db.schema.table")

    def test_struct_indexing(self):
        t = table("db.schema.table").select(col("some_struct")['id'].as_("id"))
        self.assertEqual(t.sql, "SELECT some_struct.id AS id FROM db.schema.table")

    def test_array_constructor(self):
        query = table("DUAL").select(array(1,2,3,4).as_("array"))
        self.assertEqual(query.sql, "SELECT [ 1, 2, 3, 4 ] AS array FROM DUAL")

        query = table("DUAL").select(array(1).as_("array"))
        self.assertEqual(query.sql, "SELECT [ 1 ] AS array FROM DUAL")

        query = table("DUAL").select(array().as_("array"))
        self.assertEqual(query.sql, "SELECT [ ] AS array FROM DUAL")

        with self.assertRaises(SyntaxError) as cm:
            array(1,2,3,[2,3])
        self.assertEqual("nested arrays are not supported", str(cm.exception))

        with self.assertRaises(SyntaxError) as cm:
            array(array(1,2), array(3,4))
        self.assertEqual("nested arrays are not supported", str(cm.exception))

        with self.assertRaises(SyntaxError) as cm:
            array(1, "1")
        self.assertEqual("arrays must have the same type for all elements", str(cm.exception))

    def test_json_constructor(self):
        query = table("t1").select(json("""{"class" : {"students" : [{"name" : "Jane"}]}}""").as_("v"))
        self.assertEqual(query.sql, """SELECT JSON '{"class" : {"students" : [{"name" : "Jane"}]}}' AS v FROM t1""")



        
        




        
        
        