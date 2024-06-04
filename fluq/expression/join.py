from __future__ import annotations

from typing import Callable, Optional, List
from collections import Counter
from abc import abstractmethod

from fluq.expression.base import Expression, TableNameExpression, ValidName, QueryableExpression, JoinableExpression
from fluq.expression.operator import LogicalOperationExpression, UnNestOperatorExpression


class JoinOperationExpression(Expression):
    """a base class for all relational operations"""

    def __init__(self,
                 left: JoinOperationExpression | JoinableExpression,
                 right: JoinableExpression,
                 left_alias: Optional[str]=None,
                 right_alias: Optional[str]=None,
                 on: Optional[LogicalOperationExpression]=None):
        assert isinstance(left, JoinOperationExpression | JoinableExpression)
        assert isinstance(right, JoinableExpression)
        if on is not None:
            assert isinstance(on, LogicalOperationExpression)

        self.left = left
        self.right = right
        
        self.left_alias = ValidName(left_alias).name if left_alias is not None else None
        self.right_alias = ValidName(right_alias).name if right_alias is not None else None

        if isinstance(self.left, JoinOperationExpression):
            assert self.left_alias is None, f"JoinOperationExpression can't have an alias"
        if isinstance(self.left, QueryableExpression):
            assert self.left_alias is not None, "left QueryExpression must have an alias"
        if isinstance(self.right, QueryableExpression):
            assert self.right_alias is not None, "right QueryExpression must have an alias"
        if isinstance(self.left, UnNestOperatorExpression):
            assert self.left_alias is not None, "left UnNestOperatorExpression must have an alias"
        if isinstance(self.right, UnNestOperatorExpression):
            assert self.right_alias is not None, "right UnNestOperatorExpression must have an alias"

        
        # if both right and left aliases are not None assert they are not the same
        if (self.left_alias is not None) and (self.right_alias is not None):
            if self.left_alias == self.right_alias:
                raise TypeError(f"duplicate aliases, '{self.left_alias}'")
        self.on = on

        duplicates = [item for item, count in Counter(self.aliases()).items() if count > 1]
        if len(duplicates) > 0:
            raise TypeError(f"can't have duplicate aliases for tables, found: {', '.join(duplicates)}")
        
    @classmethod
    def from_kwargs(cls, join_type: str, **kwargs) -> JoinOperationExpression:
        assert 'left' in kwargs
        assert 'right' in kwargs
        assert 'left_alias' in kwargs
        assert 'right_alias' in kwargs
        match join_type:
            case 'inner':
                assert 'on' in kwargs
                return InnerJoinOperationExpression(**kwargs)
            case 'left':
                assert 'on' in kwargs
                return LeftJoinOperationExpression(**kwargs)
            case 'right':
                assert 'on' in kwargs
                return RightJoinOperationExpression(**kwargs)
            case 'full outer':
                assert 'on' in kwargs
                return FullOuterJoinOperationExpression(**kwargs)
            case 'cross':
                return CrossJoinOperationExpression(**kwargs)
            case _:
                raise TypeError(f"unknown join_type '{join_type}'")

    
    def aliases(self) -> List[str]:
        """recursively digs for all aliases, ignores None, to check if there are duplicates"""
        result = []
        if self.left_alias is not None:
            result.append(self.left_alias)
        elif self.right_alias is not None:
            result.append(self.right_alias)
        
        if isinstance(self.left, JoinOperationExpression):
            result += self.left.aliases()
        
        return result

    @abstractmethod
    def operator(self) -> str:
        pass

    def on_clause(self) -> str:
        return f" ON {self.on.sql}" if self.on is not None else ""

    def resolve_sql(self, side: str) -> str:
        match side:
            case "left":
                side = self.left
                alias = self.left_alias
            case "right":
                side = self.right
                alias = self.right_alias
            case _:
                raise TypeError()
        if isinstance(side, TableNameExpression | JoinOperationExpression):
            result = side.sql
            if alias is not None:
                result = f"{result} AS {alias}"
            return result
        elif isinstance(side, QueryableExpression):
            return f"({side.sql}) AS {alias}"
        else:
            raise TypeError()       

    def resolve_tokens(self, side: str):
        match side:
            case "left":
                side = self.left
                alias = self.left_alias
            case "right":
                side = self.right
                alias = self.right_alias
            case _:
                raise TypeError(f"resolve tokens only works on 'left' or 'right', got {side}")
        
        result = side.tokens()
        if isinstance(side, TableNameExpression | JoinOperationExpression | UnNestOperatorExpression):  
            if alias is not None:
                result = [*result, 'AS', alias]
            return result
        elif isinstance(side, QueryableExpression):
            return ['(' ,*result, ')', 'AS', alias]
        else:
            raise TypeError()
        
    def resolve_on_clause_tokens(self) -> List[str]:
        if self.on is None:
            return []
        else:
            return ['ON', *self.on.tokens()]
        
    def tokens(self) -> List[str]:
        left: List[str] = self.resolve_tokens("left")
        right: List[str] = self.resolve_tokens("right")
        on_clause: List[str] = self.resolve_on_clause_tokens()
        return [*left, self.operator(), *right, *on_clause]
    
    def sub_expressions(self) -> List[Expression]:
        return [self.left, self.right]


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