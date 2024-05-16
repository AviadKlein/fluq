from __future__ import annotations

from typing import Union, Tuple, Callable
from expression import *



def resolve_column_function_type_decorator(func: Callable) -> Callable:
    def wrapper(s: str | int | float | bool | Column, *args, **kwargs) -> Any:
        # resolve s so it will be a Column
        s = Column._resolve_type(s)
        # Call the original function with the new 's' and other arguments
        return func(s, *args)
    return wrapper

class Column:

    def __init__(self, *args: str | Expression | Tuple[str, str] | Tuple[Expression, str]):
        self._alias = None
        assert len(args) in [1,2], f"Column expects between 1 or 2 arguments, got {len(args)}"
        if isinstance(args[0], str): # handle as ColumnExpression
            self.expr = ColumnExpression(args[0])
        elif isinstance(args[0], Expression):
            self.expr = args[0]
        else:
            raise TypeError(f"first argument to Column needs to be either str or Expression, got {type(args[0])}")

        if len(args) == 2:
            assert isinstance(args[1], str), f"2nd optional argument to Column needs to be str, got {type(args[1])}"
            self._alias = ValidName(args[1])


    @classmethod
    def _resolve_type(cls, s: str | int | float | bool | Column) -> Column:
        if isinstance(s, (str, int, float, bool)):
            return Column(LiteralExpression(s))
        elif isinstance(s, Column):
            return s
        else:
            raise TypeError(f"only supporting str | int | float | bool | Column, got {type(s)}")
    
        
    @property
    def alias(self) -> str:
        return self._alias.name
    
    def as_(self, value: str):
        """change the alias"""
        return Column(self.expr, value)
    
    @resolve_column_function_type_decorator
    def eq(self, other: str | int | float | bool | Column) -> Column:
        return Column(Equal(self.expr, other.expr))

    @resolve_column_function_type_decorator
    def neq(self, other: str | int | float | bool | Column) -> Column:
        return Column(NotEqual(self.expr, other.expr))
    
    @resolve_column_function_type_decorator
    def gt(self, other: str | int | float | bool | Column) -> Column:
        return Column(Greater(self.expr, other.expr))
    
    @resolve_column_function_type_decorator
    def geq(self, other: str | int | float | bool | Column) -> Column:
        return Column(GreaterOrEqual(self.expr, other.expr))
    
    @resolve_column_function_type_decorator
    def lt(self, other: str | int | float | bool | Column) -> Column:
        return Column(Less(self.expr, other.expr))
    
    @resolve_column_function_type_decorator
    def leq(self, other: str | int | float | bool | Column) -> Column:
        return Column(LessOrEqual(self.expr, other.expr))
    
    def is_null(self) -> Column:
        return Column(IsNull(self.expr))
    
    def is_not_null(self) -> Column:
        return Column(IsNotNull(self.expr))
    
    def between(self, 
                from_: str | int | float | bool | Column, 
                to: str | int | float | bool | Column) -> Column:
        from_ = self._resolve_type(from_)
        to = self._resolve_type(to)
        return Column(Between(self.expr, from_.expr, to.expr))
    
    @resolve_column_function_type_decorator
    def and_(self, other: str | int | float | bool | Column) -> Column:
        return Column(And(self.expr, other.expr))
    
    @resolve_column_function_type_decorator
    def or_(self, other: str | int | float | bool | Column) -> Column:
        return Column(Or(self.expr, other.expr))
    
    @resolve_column_function_type_decorator
    def like(self, other: str | int | float | bool | Column) -> Column:
        return Column(Like(self.expr, other.expr))
    
    def negate(self) -> Column:
        return Column(LiteralExpression(0)).minus(self)
    
    @resolve_column_function_type_decorator
    def __add__(self, other: str | int | float | bool | Column) -> Column:
        return Column(Plus(self.expr, other.expr))

    @resolve_column_function_type_decorator
    def plus(self, other: str | int | float | bool | Column) -> Column:
        return self.__add__(other)
        
    @resolve_column_function_type_decorator
    def minus(self, other: str | int | float | bool | Column) -> Column:
        return Column(Minus(self.expr, other.expr))
    
    @resolve_column_function_type_decorator
    def mult(self, other: str | int | float | bool | Column) -> Column:
        return Column(Multiply(self.expr, other.expr))
    
    @resolve_column_function_type_decorator
    def divide(self, other: str | int | float | bool | Column):
        return Column(Divide(self.expr, other.expr))
    
    def when(self, condition: Column, value: str | int | float | bool | Column) -> Column:
        """only works when the expr is a CaseExpression"""
        if isinstance(self.expr, CaseExpression):
            if not isinstance(condition.expr, LogicalOperationExpression):
                condition = condition.is_not_null()
            case_expr = self.expr.add(condition.expr, self._resolve_type(value).expr)
            return Column(case_expr)
        else:
            raise TypeError("can only work on columns which have a CaseExpression, use when")
        
    def otherwise(self, value: str | int | float | bool | Column) -> Column:
        """only works when the expr is a CaseExpression"""
        if isinstance(self.expr, CaseExpression):
            case_expr = self.expr.add_otherwise(self._resolve_type(value).expr)
            return Column(case_expr)
        else:
            raise TypeError("can only work on columns which have a CaseExpression, use when")