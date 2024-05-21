from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from sparkit.expression.base import Queryable
from sparkit.expression.query import QueryExpression

# set operations    
@dataclass
class SetOperation(Queryable):
    left: Queryable
    right: Queryable

    @abstractmethod
    def symbol(self) -> str:
        pass

    def flatten(self, append_to: Optional[List[QueryExpression, Optional[SetOperation]]]=None) -> List[QueryExpression, Optional[SetOperation]]:
        """flattens left and right into a list of query expr and set operation:
        the list with n elements should look like this: (Q_1, OP_1), (Q_2, OP_2), ...., (Q_n, None)
        """
        if append_to is None:
            append_to = []
        match self.left, self.right:
            case l, r if isinstance(l, QueryExpression) and isinstance(r, QueryExpression):
                append_to.append((l, self.__class__))
                append_to.append((r, None))
            case l, r if isinstance(l, QueryExpression) and isinstance(r, SetOperation):
                append_to.append((l, self.__class__))
                append_to = r.flatten(append_to=append_to)
            case l, r if isinstance(l, SetOperation) and isinstance(r, QueryExpression):
                append_to = l.flatten(append_to=append_to)
                append_to.append((r, None))
            case l, r if isinstance(l, SetOperation) and isinstance(r, SetOperation):
                append_to = l.flatten(append_to=append_to)
                append_to = r.flatten(append_to=append_to)
        return append_to
    
    def tokens(self) -> List[str]:
        pass
                

    def unindented_sql(self) -> str:
        left = self.left.unindented_sql()
        right = None
        return f"{left}\n{self.symbol()}\n{right}"
        
@dataclass
class UnionAllSetOperation(SetOperation):

    def symbol(self) -> str:
        return "UNION ALL"
    
@dataclass
class UnionDistinctSetOperation(SetOperation):

    def symbol(self) -> str:
        return "UNION DISTINCT"
    
@dataclass
class IntersectSetOperation(SetOperation):

    def symbol(self) -> str:
        return "INTERSECT DISTINCT"
    
@dataclass
class ExceptSetOperation(SetOperation):

    def symbol(self) -> str:
        return "EXCEPT DISTINCT"
