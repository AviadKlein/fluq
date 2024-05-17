from __future__ import annotations

from typing import Tuple
from expression import *

_function_expressions = SQLFunctionExpressions()

class Column:
    """A container for SQL expressions in Frames
    
    A column is not necessarily a materialized column in a table, 
    it can be any expression that is used for 
        SELECT
        WHERE, ON, HAVING, QUALIFY
        GROUP BY, ORDER BY
        and WINDOW clauses

    Initialization:
    It is recomeded not to use __init__ directly, rather use:
      functions.col
      function.lit (for literals)
      functions.when for CASE WHEN expressions

    Usage:
        - using arithmetic operations:
        >>> hours: Column = col("hours")
        >>> minutes: Column = hours * 60

        >>> price = lit("price")
        >>> discount = col("discout")
        >>> discounted_price = price - discount
        >>> discout_percent = discount / price

        - create boolean conditions:
        >>> qualifies = (col("age") > 18) and (col("grade") > 75)
        >>> has_address = col("address").is_not_null()

        - create CASE WHEN expressions
        >>> mycol = when(col("age") > 18, "over 18").when()

        aliases:
        >>> mycol = col("user_id").as_("id")
        >>> print(mycol.alias)
        id
    """

    @classmethod
    def allowed_expressions(cls) -> Tuple[Expression]:
        return (
            ColumnExpression, 
            LiteralExpression, 
            NullExpression, 
            CaseExpression,
            AbstractOperationExpression, 
            AbstractFunctionExpression, 
            NegatedExpression)


    def __init__(self, **kwargs: str | Tuple[str, str] | Expression | Tuple[Expression, str]):
        """it is recommended to use the functions.col/lit/when methods to initialize Column 
        and to avoid the complex use of Expressions.
        
        There are 4 modes of initilization:
        either:
            name: str - a name of a physical column
        or:
            expression: Expression object of these types (and descendants): 
                ColumnExpression, LiteralExpression, NullExpression, 
                AbstractOperationExpression, AbstractFunctionExpression, NegatedExpression 

        both methods can include an optional alias: str.

        Examples:
            to initialize directly from a str that represents a physical column name:
            >>> c = Column(name="user_id")

            or with a pointer to a table
            >>> c = Column(name="table1.user_id")

            including an alias
            >>> c = Column(name="user_id", alias="id")

            including an alias via the as_ method
            >>> c = Column(name="user_id")
            >>> c = c.as_("id")

            initializing using an expression
            >>> c = Column(expression=LiteralExpression(42))
            >>> c = Column(expression=LiteralExpression(42), alias="age")
        """
        # init
        self._alias = None
        self.expr = None
        
        kws = list(kwargs.keys())
        match kws:
            case ['name']:
                return Column.__init__(self, name=kwargs['name'], alias=None)
            case ['name', 'alias']:
                return Column.__init__(self, expression=ColumnExpression(kwargs['name']), alias=kwargs['alias'])
            case ['expression']:
                return Column.__init__(self, expression=kwargs['expression'], alias=None)
            case ['expression', 'alias']:
                match kwargs['expression']:
                    case Expression():
                        expr = kwargs['expression']
                        if not isinstance(expr, Column.allowed_expressions()):
                            raise TypeError(f"supported expression types are: {Column.allowed_expressions()}, got {type(expr)}")
                        else:
                            self.expr = kwargs['expression']
                    case _:
                        raise TypeError(f"expression needs to be an Expression type, got {type(expr)}")
                match kwargs['alias']:
                    case None:
                        pass
                    case str(alias):
                        self._alias = ValidName(alias)
                    case _:
                        raise TypeError(f"alias must be str, got {type(alias)}")
            case _:
                raise TypeError(f"expected keywords are either: name, (name, alias), expression or (expression, alias). Got {kws}")


    @classmethod
    def _resolve_type(cls, s: str | int | float | bool | Column, allowed_primitives=str | int | float | bool) -> Column:
        if isinstance(s, allowed_primitives):
            return Column(expression=LiteralExpression(s), alias=None)
        elif isinstance(s, Column):
            return s
        else:
            raise TypeError(f"only supporting str | int | float | bool | Column, got {type(s)}")
    
        
    @property
    def alias(self) -> Optional[str]:
        return None if self._alias is None else self._alias.name
    
    def as_(self, value: str):
        """change the alias"""
        return Column(expression=self.expr, alias=value)
    
    def __eq__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Equal(self.expr, other.expr), alias=None)

    def __ne__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=NotEqual(self.expr, other.expr), alias=None)
    
    def __gt__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Greater(self.expr, other.expr), alias=None)
    
    def __ge__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=GreaterOrEqual(self.expr, other.expr), alias=None)
    
    def __lt__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Less(self.expr, other.expr), alias=None)
    
    def __le__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=LessOrEqual(self.expr, other.expr), alias=None)
    
    def is_null(self) -> Column:
        return Column(expression=IsNull(self.expr), alias=None)
    
    def is_not_null(self) -> Column:
        return Column(expression=IsNotNull(self.expr), alias=None)
    
    def between(self, 
                from_: str | int | float | bool | Column, 
                to: str | int | float | bool | Column) -> Column:
        from_ = self._resolve_type(from_)
        to = self._resolve_type(to)
        return Column(expression=Between(self.expr, from_.expr, to.expr), alias=None)
    
    def __and__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=And(self.expr, other.expr), alias=None)
    
    def __or__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Or(self.expr, other.expr), alias=None)
    
    def like(self, other: str | Column) -> Column:
        if not isinstance(other, str | Column):
            raise TypeError(f"like only supports str | Column, got {type(other)}")
        other = self._resolve_type(other)
        return Column(expression=Like(self.expr, other.expr), alias=None)
    
    def __neg__(self) -> Column:
        return Column(expression=NegatedExpression(self.expr), alias=None)
    
    def __add__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Plus(self.expr, other.expr), alias=None)
    
    def __sub__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Minus(self.expr, other.expr), alias=None)
    
    def __mul__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Multiply(self.expr, other.expr), alias=None)
    
    def __truediv__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Divide(self.expr, other.expr), alias=None)
    
    def __mod__(self, other: str | int | float | bool | Column) -> Column:
        other: Column = self._resolve_type(other)
        expr =  _function_expressions.FunctionExpressionMOD(X=self.expr, Y=other.expr)
        return Column(expression=expr, alias=None)
    
    def __floordiv__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        div_expr = Divide(self.expr, other.expr)
        floor_expr = _function_expressions.FunctionExpressionFLOOR(X=div_expr)
        return Column(expression=floor_expr, alias=None)
    
    def when(self, condition: Column, value: str | int | float | bool | Column) -> Column:
        """only works when the expr is a CaseExpression"""
        if isinstance(self.expr, CaseExpression):
            if not isinstance(condition.expr, LogicalOperationExpression):
                condition = condition.is_not_null()
            case_expr = self.expr.add(condition.expr, self._resolve_type(value).expr)
            return Column(expression=case_expr, alias=None)
        else:
            raise TypeError("can only work on columns which have a CaseExpression, use when")
        
    def otherwise(self, value: str | int | float | bool | Column) -> Column:
        """only works when the expr is a CaseExpression"""
        if isinstance(self.expr, CaseExpression):
            case_expr = self.expr.add_otherwise(self._resolve_type(value).expr)
            return Column(expression=case_expr, alias=None)
        else:
            raise TypeError("can only work on columns which have a CaseExpression, use when")