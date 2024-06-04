from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
from fluq.expression.base import Expression, SelectableExpression, ValidName, TerminalExpression


class AnyExpression(SelectableExpression, TerminalExpression):
    """just in case you need to solve something"""

    def __init__(self, expr: str):
        if not isinstance(expr, str):
            raise TypeError(f"expr must by of type str, got {type(expr)}")
        if len(expr) == 0:
            raise SyntaxError("can't have empty expr")

        spl = expr.split(' ')
        if len(spl) > 1:
            if spl[-2].upper() == 'AS':
                raise SyntaxError("don't create aliases within AnyExpression")
            if spl[-2][-1] == ')':
                raise SyntaxError("don't create aliases within AnyExpression")
            if ')' in spl[-1]:
                pass
            if ')' not in expr:
                raise SyntaxError("don't create aliases within AnyExpression")
        self.expr = expr

    def tokens(self) -> List[str]:
        return [self.expr]


@dataclass
class ColumnExpression(SelectableExpression, TerminalExpression):
    """when you just want to point to a column"""
    _name: str

    def __post_init__(self):
        assert isinstance(self._name, str)
        if self._name == "*":
            pass
        else:
            self._name = ValidName(self._name)

    @property
    def name(self) -> str:
        return "*" if self._name == "*" else self._name.name

    def tokens(self) -> List[str]:
        return [self.name]
    
    def __hash__(self) -> int:
        return hash(self.__class__.__name__ + self.name)


LiteralTypes = int | float | bool | str


class LiteralExpression(SelectableExpression, TerminalExpression):
    """to hold numbers, strings, booleans"""

    def __init__(self, value: LiteralTypes) -> None:
        super().__init__()
        self.value = value
        if isinstance(value, bool):
            self.sql_value = str(value).upper()
        elif isinstance(value, str):
            self.sql_value = f"'{value}'"
        elif isinstance(value, (float, int)):
            self.sql_value = str(value)
        else:
            raise TypeError()

    def tokens(self) -> str:
        return [self.sql_value]


class NegatedExpression(SelectableExpression):
    """negate an expression"""

    def __init__(self, expr: Expression) -> None:
        assert isinstance(expr, Expression)
        self.expr = expr

    def tokens(self) -> List[str]:
        head, *tail = self.expr.tokens()
        return [f'-{head}', *tail]
    
    def sub_expressions(self) -> List[Expression]:
        return [self.expr]


class NullExpression(SelectableExpression, TerminalExpression):
    """a special expression for the NULL value"""

    def tokens(self) -> List[str]:
        return ["NULL"]


class ArrayExpression(SelectableExpression):

    def __init__(self, *args: SelectableExpression):
        self.elements = list(args)

    def tokens(self) -> List[str]:
        elements_str = []
        for elem in self.elements:
            elements_str = [*elements_str, ',', *elem.tokens()]
        if len(elements_str) > 0:
            if elements_str[0] == ',':
                elements_str = elements_str[1:]
        return ['[', *elements_str ,']']
    
    def sub_expressions(self) -> List[Expression]:
        return [self.elements]


class JSONExpression(SelectableExpression, TerminalExpression):

    def __init__(self, json_str):
        self.json_str = json_str

    def tokens(self) -> List[str]:
        return ['JSON', f"'{self.json_str}'"]


class TupleExpression(SelectableExpression):

    def __init__(self, *args: LiteralTypes | ColumnExpression | LiteralExpression | TupleExpression) -> None:
        args = list(args)
        self.elements = []
        for arg in args:
            if isinstance(arg, LiteralTypes):
                self.elements.append(LiteralExpression(arg))
            elif isinstance(arg, ColumnExpression | LiteralExpression):
                self.elements.append(arg)
            else:
                raise TypeError(f"TupleExpression only supports: ColumnExpression and LiteralType, got {type(arg)}")


    def tokens(self) -> List[str]:
        result = []
        for arg in self.elements:
            result = [*result, ',', *arg.tokens()]
        if len(self.elements) > 1: # remove first comma
            result = result[1:]
        return ['(', *result ,')']
    
    def sub_expressions(self) -> List[Expression]:
        return [self.elements]


class StructExpression(SelectableExpression):
    
    def __init__(self, *exprs: SelectableExpression | Tuple[SelectableExpression, str]):
        self.exprs = []
        self.field_names = []
        for expr in list(exprs):
            if isinstance(expr, SelectableExpression):
                self.exprs.append(expr)
                self.field_names.append(None)
            elif isinstance(expr, tuple):
                if isinstance(expr[0], SelectableExpression) and isinstance(expr[1], str):
                    alias = ValidName(expr[1])
                    self.exprs.append(expr[0])
                    self.field_names.append(alias.name)
                elif isinstance(expr[0], SelectableExpression) and expr[1] is None:
                    self.exprs.append(expr[0])
                    self.field_names.append(None)
                else:
                    raise TypeError()
            else:
                raise TypeError()
        
    def tokens(self) -> List[str]:
        zipped = zip(self.exprs, self.field_names)
        result = []
        for e, fn in zipped:
            if fn is None:
                elem = e.tokens()
            else:
                elem = [*e.tokens(), 'AS', fn]
            if len(result) == 0:
                result = elem
            else:
                result = [*result, ',', *elem]
        return ['STRUCT(', *result, ')']

    def sub_expressions(self) -> List[Expression]:
        return [self.exprs]
        
