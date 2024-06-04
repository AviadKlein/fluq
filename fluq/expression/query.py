from __future__ import annotations


from dataclasses import dataclass
from typing import Callable, Optional, List

from fluq.expression.base import Expression, QueryableExpression
from fluq.expression.clause import FromClauseExpression, WhereClauseExpression, \
    GroupByClauseExpression, SelectClauseExpression, HavingClauseExpression, QualifyClauseExpression, \
    OrderByClauseExpression, LimitClauseExpression, ClauseExpression

@dataclass
class QueryExpression(QueryableExpression):
    from_clause: Optional[FromClauseExpression]=None
    where_clause: Optional[WhereClauseExpression]=None
    group_by_clause: Optional[GroupByClauseExpression]=None
    select_clause: Optional[SelectClauseExpression]=None
    having_clause: Optional[HavingClauseExpression]=None
    qualify_clause: Optional[QualifyClauseExpression]=None
    order_by_clause: Optional[OrderByClauseExpression]=None
    limit_clause: Optional[LimitClauseExpression]=None

    def __post_init__(self):
        assert isinstance(self.from_clause, FromClauseExpression) or self.from_clause is None
        assert isinstance(self.where_clause, WhereClauseExpression) or self.where_clause is None
        assert isinstance(self.group_by_clause, GroupByClauseExpression) or self.group_by_clause is None
        assert isinstance(self.select_clause, SelectClauseExpression) or self.select_clause is None
        assert isinstance(self.having_clause, HavingClauseExpression) or self.having_clause is None
        assert isinstance(self.qualify_clause, QualifyClauseExpression) or self.qualify_clause is None
        assert isinstance(self.order_by_clause, OrderByClauseExpression) or self.order_by_clause is None
        assert isinstance(self.limit_clause, LimitClauseExpression) or self.limit_clause is None


    def copy(self, 
            from_clause: Optional[FromClauseExpression]=None,
            where_clause: Optional[WhereClauseExpression]=None,
            group_by_clause: Optional[GroupByClauseExpression]=None,
            select_clause: Optional[SelectClauseExpression]=None,
            having_clause: Optional[HavingClauseExpression]=None,
            qualify_clause: Optional[QualifyClauseExpression]=None,
            order_by_clause: Optional[OrderByClauseExpression]=None,
            limit_clause: Optional[LimitClauseExpression]=None) -> QueryExpression:
        return QueryExpression(
            from_clause = self.from_clause if from_clause is None else from_clause,
            where_clause = self.where_clause if where_clause is None else where_clause,
            group_by_clause = self.group_by_clause if group_by_clause is None else group_by_clause,
            select_clause = self.select_clause if select_clause is None else select_clause,
            having_clause = self.having_clause if having_clause is None else having_clause,
            qualify_clause = self.qualify_clause if qualify_clause is None else qualify_clause,
            order_by_clause = self.order_by_clause if order_by_clause is None else order_by_clause,
            limit_clause = self.limit_clause if limit_clause is None else limit_clause
        )

    def clause_ordering(self) -> List[ClauseExpression]:
        return [
            self.select_clause,
            self.from_clause, 
            self.where_clause, 
            self.group_by_clause, 
            self.having_clause,
            self.qualify_clause,
            self.order_by_clause,
            self.limit_clause]
    
    def tokens(self) -> List[str]:
        result = []
        for clause in self.clause_ordering():
            if clause is not None:
                result = [*result, *clause.tokens()]
        return result
    
    def sub_expressions(self) -> List[Expression]:
        exprs = []
        if self.select_clause is not None:
            exprs.append(self.select_clause)
        if self.from_clause is not None:
            exprs.append(self.from_clause)
        if self.where_clause is not None:
            exprs.append(self.where_clause)
        if self.group_by_clause is not None:
            exprs.append(self.group_by_clause)
        if self.having_clause is not None:
            exprs.append(self.having_clause)
        if self.qualify_clause is not None:
            exprs.append(self.qualify_clause)
        if self.limit_clause is not None:
            exprs.append(self.limit_clause)
        if self.order_by_clause is not None:
            exprs.append(self.order_by_clause)
        return exprs
    
    
    def is_simple(self) -> bool:
        """a simple query is the following pattern: SELECT * FROM [TABLE]"""
        cond = [self.select_clause.is_select_all(), 
                self.from_clause.is_simple(),
                self.group_by_clause is None,
                self.where_clause is None,
                self.having_clause is None,
                self.qualify_clause is None,
                self.limit_clause is None,
                self.order_by_clause is None
                ]
        return all(cond)
