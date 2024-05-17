from typing import Any

from expression import Expression, CaseExpression, ColumnExpression, \
    LiteralExpression, AbstractFunctionExpression, SQLFunctionExpressions
from column import Column


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

class SQLFunctions:
    
    def create_dynamic_method(self, symbol: str, arguments):
        
        def f(*inputs: int | float | str | bool | Column) -> Column:
            inputs = list(inputs)
            assert len(inputs) == len(arguments)
            kwargs = {arg: Column._resolve_type(x).expr for arg, x in zip(arguments,inputs)}
            clazz = f"FunctionExpression{symbol}"
            clazz = getattr(self.function_expressions, clazz)
            instance: AbstractFunctionExpression = clazz(**kwargs)
            return Column(expression=instance, alias=None)
        
        return f

    def __init__(self, set_global: bool=False):
        self.function_expressions = SQLFunctionExpressions()
        for symbol, arguments in self.function_expressions._params():
            f = self.create_dynamic_method(symbol, arguments)
            if set_global:
                import __main__
                setattr(__main__, symbol.lower(), f)
            else:
                setattr(self, symbol.lower(), f)

functions = SQLFunctions(False)
            

            