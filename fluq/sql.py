from __future__ import annotations

from fluq._util import is_valid_json
from fluq.expression.base import ResultSet
from fluq.expression.function import ExistsOperatorExpression, CaseExpression, FunctionParams
from fluq.expression.literals import *
from fluq.expression.selectable import *
from fluq.expression.clause import SelectClauseExpression
from fluq.expression.query import QueryExpression
from fluq.expression.set_operation import UnionAllSetOperation
from fluq.column import Column
from fluq.column import WindowSpec # not used in this module but is importat for users

from fluq.frame import Frame


def col(name: str) -> Column:
    """create a Column based on a known column name
    
    Usage:
        >>> from fluq.sql import *
        >>> customer_id = col("id")
    """
    if not isinstance(name, str):
        raise TypeError(f"name must be of type str, got {type(name)}")
    return Column(expression=ColumnExpression(name), alias=None)

def lit(value: int | float | str | bool) -> Column:
    if not isinstance(value, int | float | str | bool):
        raise TypeError(f"lit supports the following types: int | float | str | bool, got {type(value)}")
    expr = LiteralExpression(value)
    return Column(expression=expr, alias=None)

def interval(duration: str | int) -> Column.IntervalLiteralConstructor:
    return Column.IntervalLiteralConstructor(duration=duration)

def array(*args) -> Column:
    """construct an array of type T
    Nested arrays are not supported, since type checking is complex, one can use Column objects too, 
    but these will be only checked once passed to the SQL engine
    Primitives will be wrapped with a LiteralExpression

    Raises:
        SyntaxError - Arrays of Arrays are not supported, mix of types is not supported
    
    Sournce https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types#array_type
    """
    args = list(args)
    # check if nested
    for arg in args:
        if isinstance(arg, list | tuple):
            raise SyntaxError("nested arrays are not supported")
    # check all types are the same
    if len(args) == 0:
        return Column(expression=ArrayExpression(), alias=None)    
    else:
        head, *tail = args
        for arg in tail:
            if not isinstance(arg, type(head)):
                raise SyntaxError("arrays must have the same type for all elements")
        if isinstance(head, Column):
            if any([isinstance(_.expr, ArrayExpression) for _ in args]):
                raise SyntaxError("nested arrays are not supported")
            elements = [_.expr for _ in args]
        else:
            elements = [LiteralExpression(_) for _ in args]
        expr = ArrayExpression(*elements)
        return Column(expression=expr, alias=None)
    
def json(json_str: str) -> Column:
    if not isinstance(json_str, str):
        raise TypeError("")
    else:
        if is_valid_json(json_str):
            expr = JSONExpression(json_str)
            return Column(expression=expr, alias=None)
        else:
            raise SyntaxError(f"not a valid JSON: '{json_str}'")
    
def tup(*cols: int | float | str | bool | Column) -> Column:
    """create tuples of columns literal
    
    Usage:
        >>> ids = table("ids").select(col("id"), col("parent_id"))
        >>> table("t").where(tup(col("id"), col("parent_id")).is_in(ids))
    
    """
    exprs = []
    for arg in cols:
        if isinstance(arg, int | float | str | bool):
            exprs.append(LiteralExpression(arg))
        elif isinstance(arg, Column):
            exprs.append(arg.expr)
        else:
            raise TypeError(f"arg must be int | float | str | bool | Column, got {type(arg)}")
        
    new_expr = TupleExpression(*exprs)
    return Column(expression=new_expr, alias=None)

def struct(*cols: int | float | str | bool | Column) -> Column:
    exprs = []
    aliases = []
    for arg in cols:
        if isinstance(arg, int | float | str | bool):
            exprs.append(LiteralExpression(arg))
            aliases.append(None)
        elif isinstance(arg, Column):
            exprs.append(arg.expr)
            aliases.append(arg.alias)
        else:
            raise TypeError(f"arg must be int | float | str | bool | Column, got {type(arg)}")
    zipped = list(zip(exprs, aliases))
    return Column(expression=StructExpression(*zipped), alias=None)

def exists(query: Frame) -> Column:
    expr = ExistsOperatorExpression(query=query._query_expr)
    return Column(expression=expr, alias=None)


def select(*cols: int | float | str | bool | Column) -> Frame:
    """returns a SELECT frame with no FROM"""
    from fluq.expression.clause import SelectClauseExpression
    from fluq.expression.query import QueryExpression
    expressions = []
    aliases = []
    for col in cols:
        if isinstance(col, int | float | str | bool):
            expressions.append(LiteralExpression(col))
            aliases.append(None)
        elif isinstance(col, Column):
            expressions.append(col.expr)
            aliases.append(col.alias)
    select_expr = SelectClauseExpression(expressions=expressions, aliases=aliases)
    query=QueryExpression(select_clause=select_expr)
    return Frame(queryable_expression=query)

def expr(expression: str) -> Column:
    """in case fluq does not support a specific function or a handler
    one can use this method to create a Column holding an AnyExpression
    no further logical checks will happen until the sql is used
    
    Raises:
        SyntaxError - when trying to supply an alias"""

    return Column(expression=AnyExpression(expr=expression), alias=None)

def when(condition: Column, value: int | float | str | bool | Column) -> Column:
    """
    Usage:
    >>> case = when(col.equal(2), "a").when(col.equal(3), "b").otherwise("c")
    """
    if isinstance(value, int | float | str | bool):
        value = LiteralExpression(value)
    elif isinstance(value, Column):
        value = value.expr
    elif isinstance(value, Expression):
        pass
    else:
        raise TypeError()
    return Column(expression=CaseExpression(cases=[(condition.expr, value)]), alias=None)

def table(obj: str | Column) -> Frame:
    """create a Frame from a pointer to a physical table
    
    this is the most recommended way to initialize a Frame object, 
    as using the Expression api a much harder approach
    
    Arguments:
        obj: Either a str - the physical name of the table (is checked by ValidName)
            Or a Column object whose expr is an UnNestOperatorExpression
            For example: 
            >>> table(unnest(array(1,2,3)))

    Examples:
        >>> clients = table("db.schema.clients").as_("c")
        >>> payments = table("db.schema.payments").as_("p")
        >>> query = ( 
            clients.join(payments, on=col("c.id") == col("p.client_id"), join_type='left')
                .select("c.id", "p.transaction_time", "p.transaction_value")
            )
        >>> print(query.sql)
            SELECT c.id, p.transaction_time, p.transaction_value
            FROM db.schema.clients AS c LEFT OUTER JOIN db.schema.payments as p ON c.id = p.client_id
    
    """
    from fluq.expression.base import TableNameExpression
    from fluq.expression.clause import UnNestOperatorExpression, FromClauseExpression, SelectClauseExpression
    from fluq.expression.query import QueryExpression
    match obj:
        case str(_):
            from_clause = FromClauseExpression(table=TableNameExpression(obj))    
        case Column():
            match obj.expr:
                case UnNestOperatorExpression(_):
                    from_clause = FromClauseExpression(table=obj.expr)
                case _:
                    raise SyntaxError("can't use a column that is not using UNNEST")
    query = QueryExpression(from_clause=from_clause, select_clause=SelectClauseExpression.wildcard())
    return Frame(queryable_expression=query)

def unnest(obj: Column | ResultSet) -> Column:
    from fluq.expression.clause import UnNestOperatorExpression
    match obj:
        case Column():
            expr = UnNestOperatorExpression(obj.expr)
        case ResultSet():
            expr = UnNestOperatorExpression(obj._get_expr())
        case _:
            raise TypeError()
    return Column(expression=expr, alias=None)
    


class DateTimePart:
    """
    date_part, datetime_part or timestamp_part all in one
    an object called 'datetimeparts' is created when importing fluq.sql
    Usage:
        >>> from fluq.sql import *
        >>> from fluq.sql import functions as fn, datetimeparts as dt
        >>> friday = fn.date_trunc(col("date"), dt.WEEK.FRIDAY)
        >>> query = table("t").select(friday)
        >>> print(query.sql) # Output: SELECT DATE_TRUNC( date, WEEK(FRIDAY) ) FROM t
    """

    def __init__(self, expr: Optional[DateTimePartExpression]=None):
        self.expr = None
        if expr is not None:
            assert isinstance(expr, DateTimePartExpression)
            self.expr = expr

    @property
    def ISOYEAR(self) -> DateTimePart:
        return DateTimePart(IsoYearDateTimePart())
    
    @property
    def YEAR(self) -> DateTimePart:
        return DateTimePart(YearDateTimePart())
    
    @property
    def MONTH(self) -> DateTimePart:
        return DateTimePart(MonthDateTimePart())
    
    @property
    def WEEK(self) -> DateTimePart:
        return DateTimePart(WeekDateTimePart())
    
    @property
    def ISOWEEK(self) -> DateTimePart:
        return DateTimePart(IsoWeekDateTimePart())
    
    @property
    def DAY(self) -> DateTimePart:
        return DateTimePart(DayDateTimePart())
    
    @property
    def HOUR(self) -> DateTimePart:
        return DateTimePart(HourDateTimePart())
    
    @property
    def MINUTE(self) -> DateTimePart:
        return DateTimePart(MinuteDateTimePart())
    
    @property
    def SECOND(self) -> DateTimePart:
        return DateTimePart(SecondDateTimePart())
    
    @property
    def MILLISECOND(self) -> DateTimePart:
        return DateTimePart(MilliSecondDateTimePart())
    
    @property
    def MICROSECOND(self) -> DateTimePart:
        return DateTimePart(MicroSecondDateTimePart())
    
    def _weekday_spec_check(self):
        if self.expr is None:
            raise SyntaxError("expr is None, first use DateTimePart().WEEK")
        elif not isinstance(self.expr, WeekDateTimePart):
            raise SyntaxError(f"only WeekDateTimePart supports weekday specifications")
    
    @property
    def SUNDAY(self) -> DateTimePart:
        self._weekday_spec_check()
        return DateTimePart(WeekDateTimePart('SUNDAY'))
    
    @property
    def MONDAY(self) -> DateTimePart:
        self._weekday_spec_check()
        return DateTimePart(WeekDateTimePart('MONDAY'))
    
    @property
    def TUESDAY(self) -> DateTimePart:
        self._weekday_spec_check()
        return DateTimePart(WeekDateTimePart('TUESDAY'))
    
    @property
    def WEDNESDAY(self) -> DateTimePart:
        self._weekday_spec_check()
        return DateTimePart(WeekDateTimePart('WEDNESDAY'))
    
    @property
    def THURSDAY(self) -> DateTimePart:
        self._weekday_spec_check()
        return DateTimePart(WeekDateTimePart('THURSDAY'))
    
    @property
    def FRIDAY(self) -> DateTimePart:
        self._weekday_spec_check()
        return DateTimePart(WeekDateTimePart('FRIDAY'))
    
    @property
    def SATURDAY(self) -> DateTimePart:
        self._weekday_spec_check()
        return DateTimePart(WeekDateTimePart('SATURDAY'))
    

class SQLFunctions:
    
    def create_dynamic_method(self, params: FunctionParams, is_distinct: bool=False):
        from fluq.expression.function import AbstractFunctionExpression
        
        def f(*cols: int | float | str | bool | Column | DateTimePart) -> Column:
            cols = list(cols)
            exprs = []
            for col in cols:
                if isinstance(col, int | float | str | bool):
                    exprs.append(LiteralExpression(col))
                elif isinstance(col, Column | DateTimePart):
                    exprs.append(col.expr)
                else:
                    raise TypeError(f"unsupported type: {type(col)}")
            clazz = getattr(self.function_expressions, params.clazz_name(is_distinct))
            instance: AbstractFunctionExpression = clazz(*exprs)
            return Column(expression=instance, alias=None)
        
        return f

    def __init__(self):
        from fluq.expression.function import SQLFunctionsGenerator
        self.function_expressions = SQLFunctionsGenerator()
        for params in self.function_expressions._params():
            f = self.create_dynamic_method(params=params)
            setattr(self, params.symbol.lower(), f)
            if params.supports_distinct:
                f = self.create_dynamic_method(params=params, is_distinct=True)
                setattr(self, f"{params.symbol.lower()}_distinct", f)



# module level constants
#####################################
functions = SQLFunctions() # recommend to import as fn
datetimeparts = DateTimePart() # recommend to import as dt


# Frame constructors

def from_tuples(col_names: List[str], *tuples: Tuple[int | float | bool | str, ...]) -> Frame:
    """construct a frame as a SQL statement from tuples
    very handy for unit-testing on different data
    
    Args:
        col_names: List[str] - column names for the Frame
        tuples - should keep the same 'vertical' primitive type, only supporting the union listed in the signature
        types are inferred based on the 1st tuple

    Usage:
        >>> tuples = [
        >>>     (1, 'bob'),
        >>>     (2, 'joe'),
        >>> ]
        >>> frame = Frame.from_tuples(['id', 'name'], *tuples)
        >>> print(frame.sql) # output: SELECT 1 AS id, 'bob' AS name UNION ALL SELECT 2 AS id, 'joe' AS name
    
    """

    # validate sizes
    assert len(tuples) > 0
    tuples = list(enumerate(tuples))
    n_col_names = len(col_names)
    bad_tuples = []
    for i, t in tuples:
        if len(t) != n_col_names:
            bad_tuples.append((i, t))
    if len(bad_tuples) > 0:
        raise TypeError(f"the following tuples: {[_[0] for _ in bad_tuples]} have mis-matching lengths with the number of column names")
    
    # infer type by first tuple
    types = {}
    for j, e in enumerate(tuples[0][1]):
        if not isinstance(e, int | float | bool | str):
            raise TypeError(f"in the first tuple, the {j}-th element is of an unsupported type, got {type(e)}")
        types[j] = type(e)
    
    # validate types for rest of tuples
    for i, t in tuples[1:]:
        for j, e in enumerate(t):
            if not isinstance(e, types[j]):
                raise TypeError(f"{j}-th element in {i}-th tuple is suppoesed to be of type {types[j]}, got {type(e)}")
    
    # turn into expressions
    aliases = [ValidName(cn) for cn in col_names]
    tuples = list(map(lambda t: map(lambda e: LiteralExpression(e), t[1]), tuples))
    queries = map(lambda lst: SelectClauseExpression(expressions=list(lst), aliases=aliases), tuples)
    result, *tail = list(map(lambda sc: QueryExpression(select_clause=sc), queries))
    while len(tail) > 0:
        result = UnionAllSetOperation(left=result, right=tail.pop())
    return Frame(queryable_expression=result, alias=None)