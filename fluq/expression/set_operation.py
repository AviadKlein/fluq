from __future__ import annotations

from abc import abstractclassmethod
from dataclasses import dataclass
from typing import Callable, List, Optional

from fluq.expression.base import Expression, QueryableExpression
from fluq.expression.query import QueryExpression

# set operations    
@dataclass
class SetOperation(QueryableExpression):
    left: QueryableExpression
    right: QueryableExpression

    @abstractclassmethod
    def symbol() -> str:
        pass

    def flatten(self) -> List[QueryExpression | Optional[SetOperation]]:
        """flattens left and right into a list of query expr and set operation:
        the list with n elements should look like this: Q_1, OP_1, Q_2, OP_2, ...., Q_{n-1}, OP_{n-1}, Q_n
        output length should be 2n-1
        """
        if isinstance(self.left, QueryExpression) and isinstance(self.right, QueryExpression):
            return [self.left, self, self.right]
        elif isinstance(self.left, QueryExpression) and isinstance(self.right, SetOperation):
            return [self.left, self, *self.right.flatten()]
        elif isinstance(self.left, SetOperation) and isinstance(self.right, QueryExpression):
            return [*self.left.flatten(), self, self.right]
        elif isinstance(self.left, SetOperation) and isinstance(self.right, SetOperation):
            return [*self.left.flatten(), self, *self.right.flatten()]
        else:
            raise Exception(f"unsupported types, {type(self.left)=} {type(self.right)=}")
    
    def tokens(self) -> List[str]:
        flat = self.flatten()
        if len(flat) == 3:
            return [*flat[0].tokens(), flat[1].symbol(), *flat[2].tokens()]
        result = []
        parenthesis_cnt = 0
        for obj in flat:
            if obj is None:
                pass
            elif isinstance(obj, QueryExpression):
                result = [*result, *obj.tokens()]
            elif isinstance(obj, SetOperation):
                parenthesis_cnt += 1
                result = [*result, obj.symbol(), '(']
        result += [')']*parenthesis_cnt
        return result
    
    def sub_expressions(self) -> List[Expression]:
        return [self.left, self.right]

        
@dataclass
class UnionAllSetOperation(SetOperation):

    @classmethod
    def symbol(cls) -> str:
        return "UNION ALL"
    
@dataclass
class UnionDistinctSetOperation(SetOperation):

    @classmethod
    def symbol(cls) -> str:
        return "UNION DISTINCT"
    
@dataclass
class IntersectSetOperation(SetOperation):

    @classmethod
    def symbol(cls) -> str:
        return "INTERSECT DISTINCT"
    
@dataclass
class ExceptSetOperation(SetOperation):

    @classmethod
    def symbol(cls) -> str:
        return "EXCEPT DISTINCT"
