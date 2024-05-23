from dataclasses import dataclass
from abc import abstractmethod
from typing import List

from sparkit.expression.base import Expression, LiteralTypes, LiteralExpression, NullExpression, Queryable

@dataclass
class AbstractOperationExpression(Expression):
    """an expression to denote an operation between 2 expressions
    this is supposed to serve:
    a + 2
    3 * 9
    a is NULL
    a is in ()

    etc.
    """
    left: Expression
    right: Expression
    
    def __post_init__(self):
        assert isinstance(self.left, Expression)
        assert isinstance(self.right, Expression)
    
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
                 *args: Expression | LiteralTypes | Queryable):
        assert isinstance(left, Expression)
        self.left = left
        self.is_query = False

        # assert only 1 QueryExpression
        _num_queries = sum([1 for _ in args if isinstance(_, Queryable)])
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
            msg = "list of expressions can be Expression | LiteralTypes | FutureExpression"
            msg += "\n"
            msg += f"{args} has types: ({[type(_) for _ in args]}), respectively"
            raise TypeError(msg)

    @property
    def op_str(self) -> str:
        return "IN"

    def unindented_sql(self) -> str:
        if self.is_query:
            return f"{self.left.unindented_sql()} {self.op_str} ( {self.query.sql} )"
        else:
            resolved_str = ', '.join([_.sql for _ in self._list])
            return f"{self.left.unindented_sql()} {self.op_str} ({resolved_str})"
        
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
    
class Not(NotEqual):

    def __init__(self, expr: Expression):
        super().__init__(left=expr, right=LiteralExpression(True))

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
    
    def tokens(self) -> List[str]:
        return [*self.left.tokens(), self.op_str, *self.from_.tokens(), 'AND', *self.to.tokens()]
    
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