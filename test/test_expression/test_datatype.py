from unittest import TestCase

from fluq.expression.datatype import *
from fluq.expression.selectable import ColumnExpression

class TestDataType(TestCase):

    def test_boolean(self):
        dtype = BooleanDataType()
        self.assertEqual(dtype.sql, 'BOOL')

    def test_bytes(self):
        dtype = BytesDataType()
        self.assertEqual(dtype.sql, 'BYTES')

        dtype = BytesDataType(length=9)
        self.assertEqual(dtype.sql, 'BYTES(9)')

    def test_string(self):
        dtype = StringDataType()
        self.assertEqual(dtype.sql, 'STRING')

        dtype = StringDataType(length=9)
        self.assertEqual(dtype.sql, 'STRING(9)')

    def test_date(self):
        dtype = DateDataType()
        self.assertEqual(dtype.sql, 'DATE')

    def test_datetime(self):
        dtype = DateTimeDataType()
        self.assertEqual(dtype.sql, 'DATETIME')

    def test_geography(self):
        dtype = GeographyDataType()
        self.assertEqual(dtype.sql, 'GEOGRAPHY')

    def test_interval(self):
        dtype = IntervalDataType()
        self.assertEqual(dtype.sql, 'INTERVAL')

    def test_json(self):
        dtype = JSONDataType()
        self.assertEqual(dtype.sql, 'JSON')

    def test_int(self):
        dtype = INT64DataType()
        self.assertEqual(dtype.sql, 'INT64')

    def test_numeric(self):
        dtype = NUMERICDataType()
        self.assertEqual(dtype.sql, 'NUMERIC')

        dtype = NUMERICDataType(precision=14, scale=5)
        self.assertEqual(dtype.sql, 'NUMERIC(14,5)')

    def test_bignumeric(self):
        dtype = BIGNUMERICDataType()
        self.assertEqual(dtype.sql, 'BIGNUMERIC')

        dtype = BIGNUMERICDataType(precision=14.2, scale=5)
        self.assertEqual(dtype.sql, 'BIGNUMERIC(14.2,5)')

    def test_float(self):
        dtype = FLOAT64DataType()
        self.assertEqual(dtype.sql, 'FLOAT64')

    def test_cast_expr(self):
        expr = CastExpression(ColumnExpression("a"), FLOAT64DataType())
        self.assertEqual(expr.sql, 'CAST( a AS FLOAT64 )')
    
        expr = CastExpression(ColumnExpression("a"), NUMERICDataType(precision=14,scale=5))
        self.assertEqual(expr.sql, 'CAST( a AS NUMERIC(14,5) )')

    