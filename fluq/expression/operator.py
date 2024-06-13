from dataclasses import dataclass
from abc import abstractmethod
from typing import Optional, List, Tuple, Union

from fluq.expression.base import Expression, QueryableExpression, SelectableExpression, JoinableExpression, ValidName
from fluq.expression.selectable import LiteralExpression, NullExpression
from fluq._util import resolve_literal_to_str

@dataclass
class AbstractOperationExpression(SelectableExpression):
    """an expression to denote an operation between 2 expressions
    this is supposed to serve:
    a + 2
    3 * 9
    a is NULL
    a is in ()

    etc.
    """
    left: SelectableExpression
    right: SelectableExpression
    
    def __post_init__(self):
        assert isinstance(self.left, SelectableExpression)
        assert isinstance(self.right, SelectableExpression)
    
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
    
    def tokens(self) -> List[str]:
        _left: List[str] = self.left.tokens()
        if self._wrap_left:
            _left = ['(',*_left,')']
        
        _right: List[str] = self.right.tokens()
        if self._wrap_right:
            _right = ['(',*_right,')']
        
        return [*_left, self.op_str, *_right]

    def __hash__(self) -> int:
        return hash(self.__class__.__name__ + ''.join(self.tokens()))
    
    def sub_expressions(self) -> List[Expression]:
        return [self.left, self.right]


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

    def __init__(self, left: SelectableExpression, 
                 *args: SelectableExpression | int | float | bool | str | QueryableExpression):
        assert isinstance(left, SelectableExpression)
        self.left = left
        self.is_query = False

        # assert only 1 QueryExpression
        _num_queries = sum([1 for _ in args if isinstance(_, QueryableExpression)])
        assert _num_queries <= 1

        if _num_queries == 1:
            assert len(args) == 1
            self.is_query = True
            self.query = args[0]
        elif all([isinstance(_, Expression) for _ in args]):
            self._list = args
        elif all([isinstance(_, (int, float)) for _ in args]) or \
            all([isinstance(_, bool) for _ in args]) or \
            all([isinstance(_, str) for _ in args]):
            self._list = [LiteralExpression(_) for _ in args]
        else:
            msg = "list of expressions can be SelectableExpression | int | float | bool | str"
            msg += "\n"
            msg += f"{args} has types: ({[type(_) for _ in args]}), respectively"
            raise TypeError(msg)

    @property
    def op_str(self) -> str:
        return "IN"

    def tokens(self) -> List[str]:
        if self.is_query:
            return [*self.left.tokens(), self.op_str, '(' ,*self.query.tokens(), ')']
        else:
            resolved_tokens = [_.tokens() for _ in self._list]
            resolved_tokens = [elem for lst in resolved_tokens for elem in lst]
            last_token = resolved_tokens[-1]
            zipped = zip(resolved_tokens[:-1], [',']*(len(resolved_tokens)-1))
            resolved_tokens = [elem for pair in zipped for elem in pair] + [last_token]
            return [*self.left.tokens(), self.op_str, '(', *resolved_tokens, ')']
        
    def sub_expressions(self) -> List[Expression]:
        exprs = [self.left]
        if self.is_query:
            exprs.append(self.query)
        else:
            exprs = [*exprs, *self._list]
        return exprs
    

@dataclass
class Is(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return "IS"
    
class Not(SelectableExpression):

    def __init__(self, expr: SelectableExpression):
        self.expr = expr

    def tokens(self) -> List[str]:
        internal_tokens = self.expr.tokens()
        if len(internal_tokens) == 1:
            return ['NOT', internal_tokens[0]]
        else:
            return ['NOT', '(', *internal_tokens,')']
    
    def sub_expressions(self) -> List[Expression]:
        return [self.expr]


class IsNull(Is):

    def __init__(self, left: SelectableExpression):
        super().__init__(left=left, right=NullExpression())

    def sub_expressions(self) -> List[Expression]:
        return [self.left]
    
    

class IsNotNull(Is):

    def __init__(self, left: SelectableExpression):
        super().__init__(left=left, right=Not(NullExpression()))

    def sub_expressions(self) -> List[Expression]:
        return [self.left]
    

@dataclass
class Between(SelectableExpression):
    left: SelectableExpression
    from_ : SelectableExpression
    to: SelectableExpression

    @property
    def op_str(self) -> str:
        return "BETWEEN"
    
    def tokens(self) -> List[str]:
        return [*self.left.tokens(), self.op_str, *self.from_.tokens(), 'AND', *self.to.tokens()]
    
    def sub_expressions(self) -> List[Expression]:
        return [self.left, self.from_, self.to]
    
class And(LogicalOperationExpression):

    @property
    def _wrap_left(self) -> bool:
        return True
    
    @property
    def _wrap_right(self) -> bool:
        return True
    
    @property
    def op_str(self) -> str:
        return "AND"
    

class Or(LogicalOperationExpression):

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
    
class LikeAll(Like):

    @property
    def op_str(self) -> str:
        return f"{super().op_str} ALL"
    
class LikeAny(Like):

    @property
    def op_str(self) -> str:
        return f"{super().op_str} ANY"
    
class LikeSome(Like):

    @property
    def op_str(self) -> str:
        return f"{super().op_str} SOME"
    

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

@dataclass
class PositionKeyword:
    """
    Source: https://cloud.google.com/bigquery/docs/reference/standard-sql/functions-and-operators#array_subscript_operator
    """
    value: int

    @abstractmethod
    def symbol(self) -> str:
        return self.__class__.__name__


class IndexOperatorExpression(SelectableExpression):
    """used to denote access to columns, structs"""

    def __init__(self, expr: SelectableExpression, index: int | str | PositionKeyword):
        self.expr = expr
        if isinstance(index, int):
            if index < 0:
                raise SyntaxError(f"can't index with negative numbers, got {index}")
            self._type = 'array_index'
            self._value = index
        elif isinstance(index, str):
            self._type = 'struct_name'
            self._value = index
        elif isinstance(index, PositionKeyword):
            self._type = 'position_keyword'
            self._value = index

    def resolve_index_token(self) -> str:
        match self._type:
            case 'array_index':
                return str(self._value)
            case 'struct_name':
                return self._value
            case 'position_keyword':
                return f"{self._value.symbol()}({self._value.value})"

    def tokens(self) -> List[str]:
        *init, last = self.expr.tokens()
        if self._type == 'struct_name':
            return [*init, f"{last}.{self.resolve_index_token()}"]
        else:
            return [*init, f"{last}[", self.resolve_index_token(), ']']
        
    def sub_expressions(self) -> List[Expression]:
        return [self.expr]
    

@dataclass        
class UnNestOperatorExpression(SelectableExpression, JoinableExpression):
    expr: Expression

    def __post_init__(self):
        if not isinstance(self.expr, Expression):
            raise TypeError()
        
    def tokens(self) -> List[str]:
        return ['UNNEST(', *self.expr.tokens() ,')']
    
    def __hash__(self):
        return hash(''.join(self.tokens()))
    
    def sub_expressions(self) -> List[Expression]:
        return [self.expr]
    
@dataclass
class PivotOperatorExpression(Expression):
    pivot_alias: Optional[str]
    aggs: List[Tuple[SelectableExpression, Optional[ValidName]]]
    pivot_expr: SelectableExpression
    pivot_values: List[str | int | bool | float]

    def __post_init__(self):
        if not isinstance(self.aggs, list):
            raise TypeError()
        if len(self.aggs) == 0:
            raise TypeError()
        for expr, op_vn in self.aggs:
            if not isinstance(expr, SelectableExpression):
                raise TypeError()
            if op_vn is not None:
                if not isinstance(op_vn, ValidName):
                    raise TypeError()
        if not isinstance(self.pivot_expr, SelectableExpression):
            raise TypeError()
        if not isinstance(self.pivot_values, list):
            raise TypeError()
        if len(self.pivot_values) == 0:
            raise TypeError()
        for value in self.pivot_values:
            if not isinstance(value, str | int | bool | float):
                raise TypeError()
            
    def _pivot_values_tokens(self) -> List[str]:
        head, *tail = self.pivot_values
        result = [resolve_literal_to_str(head)]
        for value in tail:
            result += [',', resolve_literal_to_str(value)]
        return result
    
    @staticmethod
    def _resolve_agg_tokens(expr: SelectableExpression, 
                            optional_name: Optional[ValidName]) -> List[str]:
        result = expr.tokens()
        if optional_name is not None:
            result += ['AS', optional_name.name]
        return result

    def _aggs_tokens(self) -> List[str]:
        head, *tail = self.aggs
        expr, op_vn = head
        result = self._resolve_agg_tokens(expr, op_vn)
        for elem in tail:
            result += [',', *self._resolve_agg_tokens(elem[0], elem[1])]
        return result
    
    def tokens(self) -> List[str]:
        result = ['PIVOT', '(', 
                *self._aggs_tokens(),
                'FOR', *self.pivot_expr.tokens(), 
                'IN', '(', *self._pivot_values_tokens(),')' ,
                ')']
        if self.pivot_alias is not None:
            result += ['AS', self.pivot_alias]
        return result
    
    def sub_expressions(self) -> List[Expression]:
        return [*self.aggs, self.pivot_expr]
