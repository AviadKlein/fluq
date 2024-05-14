from typing import Any

from expression import Expression, CaseExpression, LiteralExpression
from column import Column


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
    return Column(CaseExpression([(condition.expr, value)]))