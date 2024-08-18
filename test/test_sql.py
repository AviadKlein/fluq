from fluq.sql import *
from fluq.sql import functions as fn, datetimeparts as dt

from unittest import TestCase

class TestSql(TestCase):

    def test_from_tuples(self):
        tuples = [(1, 'bob'), (2, 'joe'), (3, 'tim')]
        col_names = ['id', 'name']
        frame = from_tuples(col_names, *tuples)
        self.assertIsInstance(frame, Frame)
        self.assertEqual(frame.sql.str, "SELECT 1 AS id, 'bob' AS name UNION ALL ( SELECT 3 AS id, 'tim' AS name UNION ALL ( SELECT 2 AS id, 'joe' AS name ) )")

    def test_from_tuples_mismatched_column_length(self):
        col_names = ['id', 'name']
        tuples = [
            (1, 'bob'),
            (2, 'joe', 'extra')
        ]
        with self.assertRaises(TypeError) as cm:
            from_tuples(col_names, *tuples)
        self.assertEqual(str(cm.exception), "the following tuples: [1] have mis-matching lengths with the number of column names")

    def test_from_tuples_type_validation(self):
        col_names = ['id', 'name']
        tuples = [
            (1, 'bob'),
            (2, 3)
        ]
        with self.assertRaises(TypeError) as cm:
            from_tuples(col_names, *tuples)
        self.assertEqual(str(cm.exception), "1-th element in 1-th tuple is suppoesed to be of type <class 'str'>, got <class 'int'>")

    def test_from_tuples_empty_tuples(self):
        col_names = ['id', 'name']
        tuples = []
        with self.assertRaises(AssertionError):
            from_tuples(col_names, *tuples)

    def test_from_tuples_unsupported_type(self):
        col_names = ['id', 'name', 'cond', 'measure', 'error']
        tuples = [
            (1, 'bob', True, 3.14, None),
        ]
        with self.assertRaises(TypeError) as cm:
            from_tuples(col_names, *tuples)
        self.assertEqual(str(cm.exception), "in the first tuple, the 4-th element is of an unsupported type, got <class 'NoneType'>")

    def test_not(self):
        c = lit(True)
        self.assertEqual((~c).expr.sql.str, "NOT TRUE")
        self.assertEqual(c.not_().expr.sql.str, "NOT TRUE")

        c = col("date") >= '2013-06-09'
        self.assertEqual((~c).expr.sql.str, "NOT ( date >= '2013-06-09' )")
        self.assertEqual(c.not_().expr.sql.str, "NOT ( date >= '2013-06-09' )")

    def test_multiple_where(self):
        t = table("some.table").where(col("date") > '2013-06-09').where(col("date") < '2017-04-10')
        self.assertEqual(t.sql.str, "SELECT * FROM some.table WHERE ( date > '2013-06-09' ) AND ( date < '2017-04-10' )")

        t = table("some.table").where(col("date") > '2013-06-09').select("id", "name").where(col("date") < '2017-04-10')
        self.assertEqual(t.sql.str, "SELECT id, name FROM some.table WHERE ( date > '2013-06-09' ) AND ( date < '2017-04-10' )")

    def test_query_with_column_and_then_where(self):
        t = table("some.table").where(col("date") > '2013-06-09').group_by(col("date")).agg(fn.sum(col("value")).as_("value"))
        t2 = t.with_column("vsqrt", fn.sqrt(col("value"))).with_column("vcbrt", fn.cbrt(col("value")))
        t3 = t2.where(col("vsqrt") > 5)
        self.assertEqual(t3.sql.str, """SELECT *, CBRT( value ) AS vcbrt FROM ( SELECT *, SQRT( value ) AS vsqrt FROM ( SELECT date, SUM( value ) AS value FROM ( SELECT * FROM some.table WHERE date > '2013-06-09' ) AS table GROUP BY date ) ) WHERE vsqrt > 5""")
    
    def test_wilcard_is_default(self):
        t = table("some.table")
        self.assertEqual(t.sql, "SELECT * FROM some.table")
    
    def test_single_col(self):
        t = table("some.table").select(col("a"))
        self.assertEqual(t.sql, "SELECT a FROM some.table")

    def test_expr(self):
        t = table("some.table").select(expr("foo(2, 2)").as_("calc"))
        self.assertEqual(t.sql, "SELECT foo(2, 2) AS calc FROM some.table")

    def test_interval(self):
        t = table("some.table").select(col("date") + interval(2).DAY)
        self.assertEqual(t.sql, "SELECT date + INTERVAL 2 DAY FROM some.table")

    def test_interval_conversion(self):
        t = table("some.table").select(col("date") + interval(2).DAY.to("MINUTE"))
        self.assertEqual(t.sql, "SELECT date + INTERVAL 2 DAY TO MINUTE FROM some.table")

    def test_column_cast(self):
        c = col("a").cast.DATE
        self.assertEqual(c.expr.sql, 'CAST( a AS DATE )')
        self.assertEqual(c.cast.BIGDECIMAL.expr.sql, 'CAST( CAST( a AS DATE ) AS BIGNUMERIC )')
    
    def test_negation(self):
        query = table("table").select(-lit(3))
        self.assertEqual(query.sql, "SELECT -3 FROM table")

    def test_isin(self):
        query = table("table").where(col("id").is_in(1,2,3)).select("*")
        self.assertEqual(query.sql, "SELECT * FROM table WHERE id IN ( 1, 2, 3 )")

        query = table("table").where(col("id").is_in(lit(2), lit(4))).select("*")
        self.assertEqual(query.sql, "SELECT * FROM table WHERE id IN ( 2, 4 )")

    def test_isin_query(self):
        inner_query = table("t1").where(col("`date`") > lit('2024-01-01')).select("id")
        query = table("t2").where(col("id").is_in(inner_query)).select("id")
        print(query.sql)

    def test_tuple(self):
        query = table("t1").where(tup(col("id"), col("date")).is_in(lit(123), lit('2024-01-01'))).select("id")
        self.assertEqual(query.sql, "SELECT id FROM t1 WHERE ( id, date ) IN ( 123, '2024-01-01' )")
    
    def test_select(self):
        self.assertEqual(select(1,2,3).sql, "SELECT 1, 2, 3")
        self.assertEqual(select(1,lit(5),3).sql, "SELECT 1, 5, 3")
        self.assertEqual(select(array(1, 3).as_("arr")).sql, "SELECT [ 1, 3 ] AS arr")

    def test_exists(self):
        t = select(exists(table("t1").select("a", "b")).as_("result"))
        self.assertEqual(t.sql, "SELECT EXISTS ( SELECT a, b FROM t1 ) AS result")

    
    def test_struct(self):
        self.assertEqual(select(struct(1,2)).sql, "SELECT STRUCT( 1, 2 )")
        self.assertEqual(select(struct(1,lit(2).as_("A"))).sql, "SELECT STRUCT( 1, 2 AS A )")
        self.assertEqual(select(struct(1,lit(2).as_("A"), struct(col("name").as_("name"), col("age").as_("age")))).sql, 
                         "SELECT STRUCT( 1, 2 AS A, STRUCT( name AS name, age AS age ) )")
        
    def test_unnest_in_select(self):
        query = table("t1").select(col("id"), unnest(col("arr")).as_("arr"))
        self.assertEqual(query.sql, "SELECT id, UNNEST( arr ) AS arr FROM t1")

    def test_unnest_in_from(self):
        query = table(unnest(array(1,2,3)))
        self.assertEqual(query.sql, "SELECT * FROM UNNEST( [ 1, 2, 3 ] )")

    def test_unnest_in_join(self):
        query = table("t1").as_("t1").cartesian(unnest(array(1,2,3)).as_("arr"))
        self.assertEqual(query.sql, "SELECT * FROM t1 AS t1 CROSS JOIN UNNEST( [ 1, 2, 3 ] ) AS arr")

    def test_coalesce(self):
        self.assertEqual(select(fn.coalesce(col("a"), col("b"), 0).as_("result")).sql, "SELECT COALESCE( a, b, 0 ) AS result")

    def test_over(self):
        expr = fn.sum(col("value")).over(WindowSpec().partition_by(col("a"), col("b")).order_by(col("c").asc(), col("d").desc())).expr
        self.assertEqual("SUM( value ) OVER ( PARTITION BY a, b ORDER BY c ASC NULLS FIRST, d DESC NULLS FIRST )", expr.sql.str)

        expr = fn.sum(col("value")).over(WindowSpec().partition_by(col("a"), col("b")).order_by(col("c").asc(), col("d").desc()).rows_between(-10,10)).expr
        self.assertEqual("SUM( value ) OVER ( PARTITION BY a, b ORDER BY c ASC NULLS FIRST, d DESC NULLS FIRST ROWS BETWEEN 10 PRECEDING AND 10 FOLLOWING )", expr.sql.str)

    def test_pivot(self):
        query = table("t").pivot(by_col="month").in_values('jan', 'feb', 'mar').agg(fn.sum(col("value")).as_("value"))
        expected = ['SELECT', '*', 'FROM', 't', 'AS', 't', 'PIVOT', '(', 'SUM(', 'value', ')', 'AS', 'value', 'FOR', 'month', 'IN', '(', "'jan'", ',', "'feb'", ',', "'mar'", ')', ')']
        self.assertListEqual(query._get_expr().tokens(), expected)

    def test_pivot_is_not_simple(self):
        query = table("t").pivot(by_col="month").in_values('jan', 'feb', 'mar').agg(fn.sum(col("value")).as_("value"))
        self.assertFalse(query._is_simple())

    def test_pivot_join(self):
        query1 = table("t1").pivot(by_col="month").in_values('jan', 'feb', 'mar').agg(fn.sum(col("value")).as_("value"))
        query2 = table("t2").pivot(by_col="month").in_values('jan', 'feb', 'mar').agg(fn.sum(col("value")).as_("value2"))
        query = query1.as_("q1").join(query2.as_("q2"), on=col("q1.month") == col("q2.month"), join_type='inner')
        self.assertListEqual(query._get_expr().tokens(), ['SELECT', '*', 'FROM', '(', 'SELECT', '*', 'FROM', 't1', 'AS', 't1', 'PIVOT', '(', 'SUM(', 'value', ')', 'AS', 'value', 'FOR', 'month', 'IN', '(', "'jan'", ',', "'feb'", ',', "'mar'", ')', ')', ')', 'AS', 'q1', 'INNER JOIN', '(', 'SELECT', '*', 'FROM', 't2', 'AS', 't2', 'PIVOT', '(', 'SUM(', 'value', ')', 'AS', 'value2', 'FOR', 'month', 'IN', '(', "'jan'", ',', "'feb'", ',', "'mar'", ')', ')', ')', 'AS', 'q2', 'ON', 'q1.month', '=', 'q2.month'])
    
    def test_examples_1(self):
        query = table("db.schema.table1").select("id")

        print(query.sql) 

        t = table("db.schema.table1")
        print(t.sql)
        print(type(t))

    def test_examples_2(self):
        from fluq.sql import table, col, lit, functions as fn
        from datetime import date

        # create a literal with the current year
        current_year = lit(date.today().year)

        query = table("some.table").select(
            (current_year - col("year_joined")).as_("years_since_joined"),
            (col("orders")**2).as_("orders_squared"),
            col("sum_transactions")*lit(1-0.17).as_("sum_transactions_net"),
            fn.exp(3)
        )

        print(query.sql)

    def test_examples_3(self):
        from fluq.sql import table, col

        query = table("db.customers").where(
            (col("date_joined") > '2024-01-01') &
            (col("salary") < 5000) &
            (col("address").is_not_null()) & 
            (col("country") == 'US') &
            (col("indutry").is_in('food', 'services'))
        ).select("id", "name", "address")

        print(query.sql)

    def test_examples_4(self):
        query: Frame = select(col("a"), col("b"), col("c"))
        filtered = query._get_expr().filter(lambda e: e.tokens()[0] == "a")
        self.assertEqual(filtered[0]._name.name, "a")

    def test_datetimepart_example(self):
        friday = fn.date_trunc(col("date"), dt.WEEK.FRIDAY)
        query = table("t").select(friday)
        self.assertEqual(query.sql, "SELECT DATE_TRUNC( date, WEEK(FRIDAY) ) FROM t")

    def test_bug1(self):
        query = (
            table("t1").
            group_by(col("a"), col("b")).
            agg(fn.sum(col("value")).as_("total_value")).
            order_by(col("a"), col("b"))
        ).with_column("pct_value", fn.sum("total_value").over(WindowSpec().partition_by(col("a"))))
        self.assertEqual(query.sql.str, "SELECT *, SUM( 'total_value' ) OVER ( PARTITION BY a ) AS pct_value FROM ( SELECT a, b, SUM( value ) AS total_value FROM t1 GROUP BY a, b ORDER BY a ASC NULLS FIRST, b ASC NULLS FIRST )")

    def test_expr_bug(self):
        query = select(lit(1).cast.STRING)
        self.assertEqual("SELECT CAST( 1 AS STRING )", query.sql.str)

