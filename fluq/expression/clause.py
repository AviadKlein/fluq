from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from fluq.expression.base import *
from fluq.expression.base import Expression
from fluq.expression.join import *
from fluq.expression.literals import OrderBySpecExpression
from fluq.expression.operator import LogicalOperationExpression, And, Or, UnNestOperatorExpression
from fluq.expression.selectable import ColumnExpression



# Clauses
class ClauseExpression(Expression):
    """abstract for clauses (i.e. Select, From, Where, ...)"""

class SelectClauseExpression(ClauseExpression):

    def __init__(self, expressions: List[SelectableExpression], aliases: List[Optional[ValidName]], distinct: bool= False):
        if len(expressions) != len(aliases):
            raise TypeError(f"got differing length of expressions: {len(expressions)} and aliases: {len(aliases)}, inputs were: {expressions=} and {aliases=}")
        self.expressions = []
        self.aliases = []
        self._distinct = distinct
        for arg in zip(expressions, aliases):
            expr, alias = self._resolve_arg(arg)
            self.expressions.append(expr)
            self.aliases.append(alias)

    def copy(self, expressions:Optional[List[SelectableExpression]]=None, 
             aliases: Optional[List[Optional[ValidName]]]=None, 
             distinct: Optional[bool]=None) -> SelectClauseExpression:
        return SelectClauseExpression(
            expressions=self.expressions if expressions is None else expressions,
            aliases=self.aliases if aliases is None else aliases,
            distinct=self._distinct if distinct is None else distinct
        )
    
    def distinct(self) -> SelectableExpression:
        return self.copy(distinct=True)
        

    @property
    def _has_wilcard(self) -> bool:
        return ColumnExpression("*") in self.expressions
    
    def is_select_all(self) -> bool:
        cond = len(self.expressions) == 1
        cond &= self._has_wilcard
        return cond

    def _resolve_arg(self, arg: SelectableExpression | Tuple[SelectableExpression, Optional[ValidName | str]]) -> Tuple[SelectableExpression, Optional[ValidName | str]]:
        if not isinstance(arg, tuple):
            if not isinstance(arg, SelectableExpression):
                raise TypeError(f"expr type is not supported, got: {type(arg)}, expected: SelectableExpression")
            if arg == ColumnExpression("*"):
                assert not self._has_wilcard, """can only have 1 ColumnExpression("*")"""
            return arg, None
        elif isinstance(arg, tuple):
            assert len(arg) == 2
            expr, optional_alias = arg
            if not isinstance(expr, SelectableExpression):
                raise TypeError(f"expr type is not supported, got: {type(expr)}, expected: SelectableExpression")
            assert (optional_alias is None) or isinstance(optional_alias, (ValidName | str))
            if optional_alias is None:
                return self._resolve_arg(expr)
            elif isinstance(optional_alias, str):
                optional_alias = ValidName(optional_alias)
            
            if expr == ColumnExpression("*"):
                if optional_alias is not None:
                    raise AssertionError(f"""ColumnExpression("*") can't have an alias, got '{optional_alias.name}'""")
                elif self._has_wilcard:
                    raise AssertionError("""can only have 1 ColumnExpression("*")""")
            
            return expr, optional_alias


    def add(self, expression: SelectableExpression, alias: Optional[ValidName | str]=None) -> SelectClauseExpression:
        expr, optional_alias = self._resolve_arg((expression, alias))

        return SelectClauseExpression(
            expressions=[*self.expressions, expr],
            aliases=[*self.aliases, optional_alias]
        )
    
    @classmethod
    def from_args(cls, *args: Tuple[SelectableExpression, Optional[ValidName]]) -> SelectClauseExpression:
        result = SelectClauseExpression([],[])
        for arg in args:
            if not isinstance(arg, tuple):
                result = result.add(arg, None)
            elif isinstance(arg, tuple):
                assert len(arg) == 2
                result = result.add(arg[0], arg[1])
            else:
                raise TypeError(f"Only Tuple[SelectableExpressionType, Optional[ValidName]] are supported as args, got {type(arg)=}")
        return result
    
    @classmethod
    def wildcard(cls) -> SelectClauseExpression:
        return SelectClauseExpression([ColumnExpression("*")], [None])

    def resolve_expr_tokens_and_alias(self, expr: Expression, alias: Optional[ValidName]):
        expr = expr.tokens()
        if alias is not None:
            expr = [*expr, 'AS', alias.name]
        return expr

    def tokens(self) -> List[str]:
        z = list(zip(self.expressions, self.aliases))
        exprs = []
        for element in [self.resolve_expr_tokens_and_alias(expr, alias) for expr, alias in z]:
            if isinstance(element, list):
                exprs = [*exprs, ',' ,*element]
            else:
                exprs.append(',', element)
                exprs.append(element)
        if exprs[0] == ',':
            exprs = exprs[1:]
        header = ['SELECT'] if not self._distinct else ['SELECT', 'DISTINCT']
        return [*header, *exprs]
    
    def sub_expressions(self) -> List[Expression]:
        return self.expressions
                
    
class FromClauseExpression(ClauseExpression):
    """an Expression to hold the From clause
    
    usage:
    
    with 1 table:
    >>> fc = FromClauseExpression(table="db.schema.table1")
    
    1 table and alias:
    >>> fc = FromClauseExpression(table="db.schema.table1", alias="A")
    
    join another table:
    >>> fc = (
    >>>    FromClauseExpression(table="db.schema.table1", alias="A")
    >>>         .join(table="db.schema.table2", alias="B", join_type="inner", on=[LogicalExpression...])
    >>>    )

    use UNNEST operators as tables:
    >>> fc = FromClauseExpression(table=UnNestOperatorExpression(...), alias="arr")

    with expressions:
    >>> fc = FromClauseExpression(table=TableNameExpression("db.schema.table1"), alias="A")
    or with JoinOperationExpression
    >>> fc = FromClauseExpression(join_expression=JoinOperationExpression(...))

    joining other tables will internally manage a JoinOperationExpression

    with sub-queries:
    >>> q: QueryAble = ...
    >>> fc = FromClauseExpression(query=q, alias="t")
    """
    
    def __init__(self, **kwargs) -> None:
        match len(kwargs):
            case 1:
                key = list(kwargs.keys())[0]
                match key:
                    case 'table' | 'join_expression' :
                        item = kwargs[key]
                        assert isinstance(item, str | TableNameExpression | JoinOperationExpression | UnNestOperatorExpression)
                        if isinstance(item, str):
                            item = TableNameExpression(item)
                        self.from_item = item
                        self._alias = None
                    case _:
                        raise TypeError(f"when calling with 1 key word argument, only 'table' and 'join_expression' are supported, got '{key}'")
            case 2:
                key1, key2 = list(kwargs.keys())
                match (key1, key2):
                    case ('table', 'alias'):
                        table_like = kwargs[key1]
                        alias = kwargs[key2]
                        assert isinstance(table_like, str | TableNameExpression | UnNestOperatorExpression)
                        if isinstance(table_like, str):
                            table_like = TableNameExpression(table_like)
                        assert isinstance(alias, str)
                        self._alias = ValidName(alias)
                        self.from_item = table_like
                    case ('query', 'alias'):
                        query = kwargs[key1]
                        alias = kwargs[key2]
                        assert isinstance(query, QueryableExpression)
                        assert isinstance(alias, str)
                        self._alias = ValidName(alias)
                        self.from_item = query
                    case _:
                        raise TypeError(f"when calling with 2 key word arguments, either ('table', 'alias') or ('query', 'alias') are supported, got '{key1}' and '{key2}'")
            case _:
                raise TypeError("only supporting kwargs of length 1 or 2")
            
    @property
    def alias(self) -> Optional[str]:
        if (self._alias is None) or isinstance(self.from_item, JoinOperationExpression):
            return None
        else:
            return self._alias.name
            
    def cross_join(self, table: str | TableNameExpression, 
             alias: Optional[str]) -> FromClauseExpression:
        assert isinstance(table, str | TableNameExpression)
        if isinstance(table, str):
            table = TableNameExpression(table)
        if alias is not None:
            assert isinstance(alias, str)
            alias = ValidName(alias)
        join_expression = CrossJoinOperationExpression(
            left=self.from_item,
            right=table,
            left_alias=self.alias,
            right_alias=alias.name if alias is not None else None
        )
        return FromClauseExpression(join_expression=join_expression)
    
    def join(self, table: str | TableNameExpression, 
             alias: Optional[str], 
             join_type: str, 
             on: LogicalOperationExpression) -> FromClauseExpression:
        assert isinstance(table, str | TableNameExpression)
        if isinstance(table, str):
            table = TableNameExpression(table)
        if alias is not None:
            assert isinstance(alias, str)
            alias = ValidName(alias)
        assert isinstance(on, LogicalOperationExpression)
        match join_type:
            case "inner":
                join_expression = InnerJoinOperationExpression(
                    left=self.from_item,
                    right=table,
                    left_alias=self.alias,
                    right_alias=alias.name if alias is not None else None,
                    on=on
                )
            case "left":
                join_expression = LeftJoinOperationExpression(
                    left=self.from_item,
                    right=table,
                    left_alias=self.alias,
                    right_alias=alias.name if alias is not None else None,
                    on=on
                )
            case "right":
                join_expression = RightJoinOperationExpression(
                    left=self.from_item,
                    right=table,
                    left_alias=self.alias,
                    right_alias=alias.name if alias is not None else None,
                    on=on
                )
            case "full outer":
                join_expression = FullOuterJoinOperationExpression(
                    left=self.from_item,
                    right=table,
                    left_alias=self.alias,
                    right_alias=alias.name if alias is not None else None,
                    on=on
                )
            case _:
                raise TypeError(f"supported join types are 'inner', 'left', 'right', 'full outer', \
                                got '{join_type}'")
        
        return FromClauseExpression(join_expression=join_expression)
    
    def is_simple(self) -> bool:
        """a simple from clause point to 1 table only"""
        return isinstance(self.from_item, TableNameExpression)
    
    def tokens(self) -> List[str]:
        from_item_tkns = self.from_item.tokens()
        if isinstance(self.from_item, QueryableExpression):
            from_item_tkns = ['(',*from_item_tkns,')']
        if self.alias is not None:
            from_item_tkns = [*from_item_tkns, 'AS', self.alias]
        return ['FROM', *from_item_tkns]
    
    def sub_expressions(self) -> List[Expression]:
        return [self.from_item]


class PredicateClauseExpression(ClauseExpression):
    """an abstract class to suport WHERE, HAVING and QUALIFY clauses"""

    def __init__(self, logical_operation: LogicalOperationExpression):
        assert isinstance(logical_operation, LogicalOperationExpression)
        self.logical_operation = logical_operation

    def and_(self, predicate: LogicalOperationExpression):
        assert isinstance(predicate, LogicalOperationExpression)
        new_predicate = And(left=self.logical_operation, right=predicate)
        return self.__class__(new_predicate)
    
    def or_(self, predicate: LogicalOperationExpression):
        assert isinstance(predicate, LogicalOperationExpression)
        new_predicate = Or(left=self.logical_operation, right=predicate)
        return self.__class__(new_predicate)
    
    @abstractmethod
    def clause_symbol(self) -> str:
        pass
    
    def tokens(self) -> List[str]:
        return [self.clause_symbol(), *self.logical_operation.tokens()]

    def sub_expressions(self) -> List[Expression]:
        return [self.logical_operation]
    
    

class WhereClauseExpression(PredicateClauseExpression):
    
    def clause_symbol(self) -> str:
        return "WHERE"
    

class HavingClauseExpression(PredicateClauseExpression):
    
    def clause_symbol(self) -> str:
        return "HAVING"


class QualifyClauseExpression(PredicateClauseExpression):
    
    def clause_symbol(self) -> str:
        return "QUALIFY"


class GroupByClauseExpression(ClauseExpression):

    def __init__(self, *groupable_items: SelectableExpression):
        groupable_items = list(groupable_items)
        if len(groupable_items) != len(set(groupable_items)):
            raise TypeError("got duplicates in grouping items")
        # check types
        all_are_expressions = all([isinstance(_, SelectableExpression) for _ in groupable_items])
        if not all_are_expressions:
            raise TypeError("expressions can only be list[int] or list[SelectableExpressionType]")
        
        self._expressions = groupable_items

    
    def tokens(self) -> List[str]:
        if len(self._expressions) == 1:
            gi_tkns = self._expressions[0].tokens()
        else:
            gi_tkns = self._expressions[0].tokens()
            for tokens in [_.tokens() for _ in self._expressions[1:]]:
                gi_tkns = [*gi_tkns, ',' ,*tokens]
        return ['GROUP BY', *gi_tkns]
    
    def sub_expressions(self) -> List[Expression]:
        return self._expressions

class OrderByClauseExpression(ClauseExpression):

    def __init__(self, *ordering_items: SelectableExpression | Tuple[SelectableExpression, OrderBySpecExpression]):
        ordering_items = list(ordering_items)
        all_expressions_or_tuples = all([isinstance(_, (tuple, SelectableExpression)) for _ in ordering_items])
        if not all_expressions_or_tuples:
            raise TypeError("input must be a list with arguments that are either SelectableExpressionType or Tuple[SelectableExpressionType, OrderBySpecExpression]")
        
        self._expressions = []
        for arg in ordering_items:
            if isinstance(arg, SelectableExpression):
                self._expressions.append((arg, OrderBySpecExpression()))
            elif isinstance(arg, tuple):
                assert len(arg) == 2
                expr, orderbyspec = arg
                assert isinstance(expr, SelectableExpression)
                assert isinstance(orderbyspec, OrderBySpecExpression)
                self._expressions.append((expr, orderbyspec))
            else:
                TypeError()
        _keys = [_[0] for _ in self._expressions]
        if len(_keys) != len(set(_keys)):
            raise TypeError("duplicate ordering items")

    
    def resolve_expression_sql(self) -> str:
        result = []
        for expr, orderbyspec in self._expressions:
            result.append(f"{expr.unindented_sql()} {orderbyspec.unindented_sql()}")
        return ', '.join(result)
    
    def tokens(self) -> List[str]:
        head, *tail = self._expressions
        e, o = head
        result = [*e.tokens(), *o.tokens()]
        for expr, obs in tail:
            result = [*result, ',', *expr.tokens(), *obs.tokens()]
      
        return ['ORDER BY', *result]
    
    def sub_expressions(self) -> List[Expression]:
        return self._expressions


class LimitClauseExpression(ClauseExpression, TerminalExpression):

    def __init__(self, limit: int, offset: Optional[int]=None):
        assert limit > 0 and isinstance(limit, int)
        if offset is not None:
            assert offset > 0 and isinstance(offset, int)
        self.limit = limit
        self.offset = offset
    
    def tokens(self) -> List[str]:
        _offset = "" if self.offset is None else f" OFFSET {self.offset}"
        return ['LIMIT', f"{self.limit}{_offset}"]
