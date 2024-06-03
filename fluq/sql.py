from fluq._util import is_valid_json
from fluq.expression.base import *
from fluq.expression.function import *
from fluq.expression.clause import *
from fluq.expression.query import *
from fluq.column import Column
from fluq.expression.selectable import *
from fluq.frame import Frame


def col(name: str) -> Column:
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
    match obj:
        case Column():
            expr = UnNestOperatorExpression(obj.expr)
        case ResultSet():
            expr = UnNestOperatorExpression(obj._get_expr())
        case _:
            raise TypeError()
    return Column(expression=expr, alias=None)
    

class SQLFunctions:
    
    def create_dynamic_method(self, params: FunctionParams, is_distinct: bool=False):
        
        def f(*cols: int | float | str | bool | Column) -> Column:
            cols = list(cols)
            exprs = []
            for col in cols:
                if isinstance(col, int | float | str | bool):
                    exprs.append(LiteralExpression(col))
                elif isinstance(col, Column):
                    exprs.append(col.expr)
                else:
                    raise TypeError(f"unsupported type: {type(col)}")
            clazz = getattr(self.function_expressions, params.clazz_name(is_distinct))
            instance: AbstractFunctionExpression = clazz(*exprs)
            return Column(expression=instance, alias=None)
        
        return f

    def __init__(self):
        self.function_expressions = SQLFunctionsGenerator()
        for params in self.function_expressions._params():
            f = self.create_dynamic_method(params=params)
            setattr(self, params.symbol.lower(), f)
            if params.supports_distinct:
                f = self.create_dynamic_method(params=params, is_distinct=True)
                setattr(self, f"{params.symbol.lower()}_distinct", f)

functions = SQLFunctions()