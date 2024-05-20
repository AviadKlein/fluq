from typing import Any, List

from expression import Expression, CaseExpression, ColumnExpression, \
    LiteralExpression, AbstractFunctionExpression, SQLFunctionExpressions, \
    FromClauseExpression, TableNameExpression, SelectClauseExpression, QueryExpression
from column import Column
from frame import Frame


def col(name: str) -> Column:
    if not isinstance(name, str):
        raise TypeError(f"name must be of type str, got {type(name)}")
    return Column(expression=ColumnExpression(name), alias=None)

def lit(value: int | float | str | bool) -> Column:
    if not isinstance(value, int | float | str | bool):
        raise TypeError(f"lit supports the following types: int | float | str | bool, got {type(value)}")
    expr = LiteralExpression(value)
    return Column(expression=expr, alias=None)

def when(condition: Column, value: Any) -> Column:
    """
    Usage:
    >>> case = when(col.equal(2), "a").when(col.equal(3), "b").otherwise("c")
    """
    if isinstance(value, (int, float, str, bool)):
        value = LiteralExpression(value)
    elif isinstance(value, Column):
        value = value.expr
    elif isinstance(value, Expression):
        pass
    else:
        raise TypeError()
    return Column(expression=CaseExpression([(condition.expr, value)]), alias=None)

def table(db_path: str) -> Frame:
    """create a Frame from a pointer to a physical table
    
    this is the most recommended way to initialize a Frame object, 
    as using the Expression api a much harder approach
    
    Arguments:
        db_path: str - the physical name of the table (is checked by ValidName)

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
    from_clause = FromClauseExpression(table=TableNameExpression(db_path))
    select_clause = SelectClauseExpression.from_args(ColumnExpression("*"))
    query = QueryExpression(from_clause=from_clause, select_clause=select_clause)
    return Frame(queryable_expression=query)

class SQLFunctions:
    
    def create_dynamic_method(self, symbol: str, arguments: List[str]):
        
        def f(*cols: Column) -> Column:
            cols = list(cols)
            if not (len(cols) == len(arguments)):
                raise TypeError(f"number of inputs ({len(cols)}) is different from number of expected arguments ({len(arguments)})")
            if not all([isinstance(col, Column) for col in cols]):
                raise TypeError("all inputs need to be columns")
            kwargs = {arg: x.expr for arg, x in zip(arguments, cols)}
            clazz = f"FunctionExpression{symbol}"
            clazz = getattr(self.function_expressions, clazz)
            instance: AbstractFunctionExpression = clazz(**kwargs)
            return Column(expression=instance, alias=None)
        
        return f

    def __init__(self, set_global: bool=False):
        self.function_expressions = SQLFunctionExpressions()
        for symbol, arguments, _ in self.function_expressions._params():
            f = self.create_dynamic_method(symbol, arguments)
            if set_global:
                import __main__
                setattr(__main__, symbol.lower(), f)
            else:
                setattr(self, symbol.lower(), f)

functions = SQLFunctions(False)