
from __future__ import annotations

from typing import Any, List, Tuple, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
import string
import re



@dataclass
class ValidName:
    """asserts that a name str is a proper valid name for columns"""
    name: str
    
    @property
    def allowed_first_chars(self) -> str:
        return ''.join(['_', *string.ascii_letters])
    
    @property
    def allowed_last_chars(self) -> str:
        return self.allowed_first_chars + string.digits
    
    @property
    def allowed_mid_chars(self) -> str:
        return self.allowed_last_chars + "."
    
    @staticmethod
    def remove_redundant_dots(s: str):
        return re.sub(r'\.+', '.', s)

    def __post_init__(self):
        if isinstance(self.name, ValidName):
            pass
        else:
            assert len(self.name) > 0, "name cannot be an empty str"
            bad_chars: List[Tuple[int, str]] = []

            for i, char in enumerate(self.name):
                bad_char_condition = (i == 0 and char not in self.allowed_first_chars)
                bad_char_condition |= (i > 0 and char not in self.allowed_mid_chars)
                if bad_char_condition:
                        bad_chars.append((i, char))
            if len(bad_chars) > 0:
                raise Exception(f"illegal name, due to bad characters in these locations: {bad_chars}")
        self.name = self.remove_redundant_dots(self.name)


@dataclass
class Indent:
    """class to hold instructions for indentation"""
    indents: int = 0
    indent_str: str = '\t'

    def render(self) -> str:
        return f"{self.indent_str*self.indents}"
    
    def __str__(self) -> str:
        return self.render()
    
    def plus1(self) -> Indent:
        return Indent(self.indents+1, self.indent_str)


class Expression(ABC):


    @abstractmethod
    def unindented_sql(self) -> str:
        pass

    @property
    def sql(self, indent: Indent = Indent()) -> str:
        return f"{indent}{self.unindented_sql()}"
    
class AnyExpression(Expression):

    def __init__(self, expr: str):
        self.expr = expr

    def unindented_sql(self) -> str:
        return self.expr
        
    

class FutureExpression(Expression):
    """this is a place holder for until I solve the issue of subqueries used in the logical:
    col IN (select from ...)"""
    

class ToLogicalMixin(Expression):

    def to_logical(self) -> LogicalOperationExpression:
        return IsNotNull(self)


class ColumnExpression(ToLogicalMixin):
    """when you just want to point to a column"""

    def __init__(self, name: str):
        self._name = ValidName(name)

    @property
    def name(self) -> str:
        return self._name.name
    
    def unindented_sql(self) -> str:
        return self.name


class Literal(ToLogicalMixin):
    
    def __init__(self, value: str | int | float | bool) -> None:
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


    def unindented_sql(self) -> str:
        return self.sql_value


class NullExpression(ToLogicalMixin):

    def unindented_sql(self) -> str:
        return "NULL"


class AbstractOperationExpression(ToLogicalMixin):
    """all operations happen between 2 expressions"""
    
    def __init__(self, left: Expression, right: Expression):
        assert isinstance(left, Expression)
        assert isinstance(right, Expression)
        self.left = left
        self.right = right
    
    @property
    def _wrap_left(self) -> bool:
        """should wrap the left hand side with parenthesis"""
        return False
    
    @property
    def _wrap_right(self) -> bool:
        """should wrap the left hand side with parenthesis"""
        return False
    
    @abstractmethod
    def op_str(self) -> str:
        """the string that will be presented in the SQL str"""
        pass

    def unindented_sql(self) -> str:
        """the SQL str"""
        _left = self.left.unindented_sql()
        if self._wrap_left:
            _left = f"({_left})"
        
        _right = self.right.unindented_sql()
        if self._wrap_right:
            _right = f"({_right})"
        return f"{_left} {self.op_str} {_right}"


class LogicalOperationExpression(AbstractOperationExpression):
    """just a flag to differentiate between logical ops to math ops"""
    pass

class MathOperationExpression(AbstractOperationExpression):
    """just a flag to differentiate between logical ops to math ops"""
    pass


class Equal(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return "="
    

class NotEqual(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return "<>"
    

class Greater(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return ">"
    

class GreaterOrEqual(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return ">="
    

class Less(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return "<"
    

class LessOrEqual(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return "<="
    

class In(LogicalOperationExpression):

    def __init__(self, left: Expression, 
                 *args: List[Expression] | List[int] | List[float] | List[bool] | List[str] | FutureExpression):
        assert isinstance(left, Expression)
        self.left = left

        # resolve list of expressions
        if isinstance(args, tuple):
            if len(args) == 1 and isinstance(args[0], FutureExpression):
                self._list = args[0]
                raise NotImplementedError("yet to implement FutureExpression")
            elif all([isinstance(_, Expression) for _ in args]):
                self._list = args
            elif all([isinstance(_, (int, float)) for _ in args]) or \
                all([isinstance(_, bool) for _ in args]) or \
                all([isinstance(_, str) for _ in args]):
                self._list = [Literal(_) for _ in args]
            else:
                msg = "list of expressions can be List[Expression] | List[int] | List[float] | List[bool] | List[str] | FutureExpression"
                msg += "\n"
                msg += f"{args} has types: ({[type(_) for _ in args]}), respectively"
                raise TypeError(msg)

    @property
    def op_str(self) -> str:
        return "IN"

    def unindented_sql(self) -> str:
        resolved_str = ', '.join([_.sql for _ in self._list])
        return f"{self.left.unindented_sql()} {self.op_str} ({resolved_str})"
    
class Not(NotEqual):

    def __init__(self, expr: Expression):
        super().__init__(left=expr, right=Literal(True))

class IsNull(Equal):

    def __init__(self, expr: Expression):
        super().__init__(left=expr, right=NullExpression())

    @property
    def op_str(self) -> str:
        return "IS"
    

class IsNotNull(NotEqual):

    def __init__(self, expr: Expression):
        super().__init__(left=expr, right=NullExpression())

    @property
    def op_str(self) -> str:
        return "IS NOT"
    
class Between(LogicalOperationExpression):

    def __init__(self, left: Expression, from_: Expression, to: Expression):
        assert isinstance(left, Expression)
        assert isinstance(from_, Expression)
        assert isinstance(to, Expression)
        self.left = left
        self.from_ = from_
        self.to = to

    @property
    def op_str(self) -> str:
        return "BETWEEN"
    
    def unindented_sql(self) -> str:
        return f"{self.left.unindented_sql()} {self.op_str} {self.from_.unindented_sql()} AND {self.to.unindented_sql()}"
    
class And(AbstractOperationExpression):

    @property
    def _wrap_left(self) -> bool:
        return True
    
    @property
    def _wrap_right(self) -> bool:
        return True
    
    @property
    def op_str(self) -> str:
        return "AND"
    

class Or(AbstractOperationExpression):

    @property
    def _wrap_left(self) -> bool:
        return True
    
    @property
    def _wrap_right(self) -> bool:
        return True
    
    @property
    def op_str(self) -> str:
        return "OR"
    
class Like(LogicalOperationExpression):
    
    @property
    def op_str(self) -> str:
        return "LIKE"
    

class Plus(MathOperationExpression):

    @property
    def op_str(self) -> str:
        return "+"
    

class Minus(MathOperationExpression):

    @property
    def op_str(self) -> str:
        return "-"
    

class Multiply(MathOperationExpression):

    @property
    def op_str(self) -> str:
        return "*"
    

class Divide(MathOperationExpression):

    @property
    def op_str(self) -> str:
        return "/"
    

class CaseExpression(Expression):

    @classmethod
    def _resolve_condition(cls, condition: Expression) -> LogicalOperationExpression:
        if isinstance(condition, LogicalOperationExpression):
            return condition
        else:
            return condition.to_logical()

    def __init__(self, cases: List[Tuple[Expression, Expression]], otherwise: Optional[Expression]=None):
        self.cases = [(self._resolve_condition(condition), value) for condition, value in cases]
        self.otherwise = otherwise

    def add(self, condition: Expression, value: Expression) -> CaseExpression:
        new_cases = [*self.cases, (self._resolve_condition(condition), value)]
        return CaseExpression(new_cases, self.otherwise)

    def add_otherwise(self, otherwise: Expression) -> CaseExpression:
        return CaseExpression(self.cases, otherwise)

    @classmethod
    def _case_to_sql(cls, operation: Expression, expr: Expression, indent: Indent) -> str:
        return f"{indent}WHEN {operation.unindented_sql()} THEN {expr.unindented_sql()}"
    
    def unindented_sql(self) -> str:
        return self.sql(indent = Indent())
    
    @property
    def sql(self, indent: Indent = Indent()) -> str:
        if len(self.cases) == 0:
            raise ValueError("can't render to sql with 0 cases")
        cases = [self._case_to_sql(operation, expr, indent.plus1()) for operation, expr in self.cases]
        cases = '\n'.join(cases)
        otherwise = "" if self.otherwise is None else f"\n{indent.plus1()}ELSE {self.otherwise.unindented_sql()}"
        return f"{indent}CASE\n{cases}{otherwise}\n{indent}END"
    


class JoinOperationExpression(Expression):
    """a base class for all relational operations"""

    def __init__(self,
                 left: Expression | JoinOperationExpression,
                 right: Expression,
                 left_alias: Optional[str]=None,
                 right_alias: Optional[str]=None,
                 on: Optional[LogicalOperationExpression]=None):
        assert isinstance(left, Expression)
        assert isinstance(right, Expression)
        if on is not None:
            assert isinstance(on, LogicalOperationExpression)

        self.left = left
        self.right = right

        if isinstance(self.left, JoinOperationExpression):
            assert self.left_alias is None, f"JoinOperationExpression can't have an alias"
        
        self.left_alias = ValidName(left_alias).name if left_alias is not None else None
        self.right_alias = ValidName(right_alias).name if right_alias is not None else None
        self.on = on

    @abstractmethod
    def operator(self) -> str:
        pass

    def on_clause(self) -> str:
        return f" {self.on.sql}" if self.on is not None else ""

    def unindented_sql(self) -> str:
        left = self.left.sql
        if self.left_alias is not None:
            left = f"{left} AS {self.left_alias}"
        right = self.right.sql
        if self.right_alias is not None:
            right = f"{right} AS {self.right_alias}"
        return f"{left} {self.operator()} {right}{self.on_clause()}"

class InnerJoinOperationExpression(JoinOperationExpression):
    
    def operator(self) -> str:
        return "INNER JOIN"
    
class LeftJoinOperationExpression(JoinOperationExpression):
    
    def operator(self) -> str:
        return "LEFT OUTER JOIN"
    
class RightJoinOperationExpression(JoinOperationExpression):
    
    def operator(self) -> str:
        return "RIGHT OUTER JOIN"
    
class FullOuterJoinOperationExpression(JoinOperationExpression):

    def operator(self) -> str:
        return "FULL OUTER JOIN"
    
class CrossJoinOperationExpression(JoinOperationExpression):

    def __init__(self, 
                 left: Expression | JoinOperationExpression, 
                 right: Expression, 
                 left_alias: str | None = None, 
                 right_alias: str | None = None):
        super().__init__(left, right, left_alias, right_alias, None)

    def on_clause(self) -> str:
        return ""
    
    def operator(self) -> str:
        return "CROSS JOIN"
    
    