from __future__ import annotations

from typing import List, Optional, Tuple

from sparkit.expression.base import *
from sparkit.expression.join import *
from sparkit.expression.operator import LogicalOperationExpression, MathOperationExpression, And, Or
from sparkit.expression.function import AnalyticFunctionExpression, AbstractFunctionExpression, CaseExpression, SelectableExpressionType



# Clauses
class ClauseExpression(Expression):
    """abstract for clauses (i.e. Select, From, Where, ...)"""

class SelectClauseExpression(ClauseExpression):

    def __init__(self, expressions: List[SelectableExpressionType], aliases: List[Optional[ValidName]]):
        assert len(expressions) == len(aliases)
        self.expressions = []
        self.aliases = []
        for arg in zip(expressions, aliases):
            expr, alias = self._resolve_arg(arg)
            self.expressions.append(expr)
            self.aliases.append(alias)

    @property
    def _has_star(self) -> bool:
        return ColumnExpression("*") in self.expressions
    
    def is_select_all(self) -> bool:
        cond = len(self.expressions) == 1
        cond &= self._has_star
        return cond

    def _resolve_arg(self, arg: SelectableExpressionType | Tuple[SelectableExpressionType, Optional[ValidName | str]]) -> Tuple[SelectableExpressionType, Optional[ValidName | str]]:
        if not isinstance(arg, tuple):
            if not isinstance(arg, self.allowed_expression_types()):
                raise TypeError(f"expr type is not supported, got: {type(arg)}, expected: [{self.allowed_expression_types()}]")
            if arg == ColumnExpression("*"):
                assert not self._has_star, """can only have 1 ColumnExpression("*")"""
            return arg, None
        elif isinstance(arg, tuple):
            assert len(arg) == 2
            expr, optional_alias = arg
            if not isinstance(expr, self.allowed_expression_types()):
                raise TypeError(f"expr type is not supported, got: {type(expr)}, expected: [{self.allowed_expression_types()}]")
            assert (optional_alias is None) or isinstance(optional_alias, (ValidName | str))
            if optional_alias is None:
                return self._resolve_arg(expr)
            elif isinstance(optional_alias, str):
                optional_alias = ValidName(optional_alias)
            
            if expr == ColumnExpression("*"):
                if optional_alias is not None:
                    raise AssertionError(f"""ColumnExpression("*") can't have an alias, got '{optional_alias.name}'""")
                elif self._has_star:
                    raise AssertionError("""can only have 1 ColumnExpression("*")""")
            
            return expr, optional_alias


    def add(self, expression: SelectableExpressionType, alias: Optional[ValidName | str]=None) -> SelectClauseExpression:
        expr, optional_alias = self._resolve_arg((expression, alias))

        return SelectClauseExpression(
            expressions=[*self.expressions, expr],
            aliases=[*self.aliases, optional_alias]
        )
    
    @staticmethod
    def allowed_expression_types():
        return tuple([
            LiteralExpression,
            ColumnExpression, 
            NullExpression, 
            LogicalOperationExpression, 
            MathOperationExpression, 
            CaseExpression,
            AbstractFunctionExpression,
            AnalyticFunctionExpression])

    @classmethod
    def from_args(cls, *args: Tuple[SelectableExpressionType, Optional[ValidName]]) -> SelectClauseExpression:
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


    def unindented_sql(self) -> str:
        z = zip(self.expressions, self.aliases)
        f = lambda expr, alias: f"{expr.sql}" + ("" if alias is None else f" AS {alias.name}")
        exprs = ', '.join([f(expr, alias) for expr, alias in z])
        return f"SELECT {exprs}"


    def tokens(self) -> List[str]:
        z = zip(self.expressions, self.aliases)
        f = lambda expr, alias: f"{expr.sql}" + ("" if alias is None else f" AS {alias.name}")
        exprs = [f(expr, alias) for expr, alias in z]
        last_expr = exprs[-1]
        zipped = zip(exprs[:-1], [',']*(len(exprs)-1))
        zipped = [elem for pair in zipped for elem in pair]
        return ['SELECT', *zipped, last_expr]

    
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
                        assert isinstance(item, str | TableNameExpression | JoinOperationExpression)
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
                        table = kwargs[key1]
                        alias = kwargs[key2]
                        assert isinstance(table, str | TableNameExpression)
                        if isinstance(table, str):
                            table = TableNameExpression(table)
                        assert isinstance(alias, str)
                        self._alias = ValidName(alias)
                        self.from_item = table
                    case ('query', 'alias'):
                        query = kwargs[key1]
                        alias = kwargs[key2]
                        assert isinstance(query, Queryable)
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
    
    def unindented_sql(self) -> str:
        # resolve item:
        from_item_str = self.from_item.unindented_sql()
        if isinstance(self.from_item, Queryable):
            from_item_str = f"({from_item_str})"
        if self.alias is not None:
            from_item_str = f"{from_item_str} AS {self.alias}"
        return f"FROM {from_item_str}"
    
    def tokens(self) -> List[str]:
        from_item_tkns = self.from_item.tokens()
        if isinstance(self.from_item, Queryable):
            from_item_tkns = ['(',*from_item_tkns,')']
        if self.alias is not None:
            from_item_tkns = [*from_item_tkns, 'AS', self.alias]
        return ['FROM', *from_item_tkns]


class PredicateClauseExpression(ClauseExpression):
    """an abstract class to suport WHERE, HAVING and QUALIFY clauses"""

    def __init__(self, predicate: LogicalOperationExpression):
        assert isinstance(predicate, LogicalOperationExpression)
        self.predicate = predicate

    def and_(self, predicate: LogicalOperationExpression):
        assert isinstance(predicate, LogicalOperationExpression)
        new_predicate = And(left=self.predicate, right=predicate)
        return self.__class__(new_predicate)
    
    def or_(self, predicate: LogicalOperationExpression):
        assert isinstance(predicate, LogicalOperationExpression)
        new_predicate = Or(left=self.predicate, right=predicate)
        return self.__class__(new_predicate)
    
    @abstractmethod
    def clause_symbol(self) -> str:
        pass
    
    def unindented_sql(self) -> str:
        return f"{self.clause_symbol()} {self.predicate.unindented_sql()}"
    
    def tokens(self) -> List[str]:
        return [self.clause_symbol(), *self.predicate.tokens()]
    
    

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

    def __init__(self, *groupable_items: SelectableExpressionType | int):
        groupable_items = list(groupable_items)
        if len(groupable_items) != len(set(groupable_items)):
            raise TypeError("got duplicates in grouping items")
        # check types
        all_are_expressions = all([isinstance(_, self.allowed_expression_types()) for _ in groupable_items])
        all_are_ints = all([isinstance(_, int) for _ in groupable_items])
        type_condition = all_are_expressions
        type_condition |= all_are_ints
        if not type_condition:
            raise TypeError("expressions can only be list[int] or list[SelectableExpressionType]")
        
        self._expressions = None
        self._positionals = None

        if all_are_expressions:
            self.is_positional = False
            self._expressions = groupable_items
        else:
            self.is_positional = True
            if not all([_ > 0 for _ in groupable_items]):
                raise TypeError("can't have non-positive positional grouping items")
            self._positionals = groupable_items

    @staticmethod
    def allowed_expression_types():
        return tuple([
            LiteralExpression,
            ColumnExpression, 
            NullExpression, 
            LogicalOperationExpression, 
            MathOperationExpression, 
            CaseExpression,
            AbstractFunctionExpression])
    
    def unindented_sql(self) -> str:
        gi_str = [str(_) for _ in self._positionals] if self.is_positional \
            else [_.unindented_sql() for _ in self._expressions]
        gi_str = ', '.join(gi_str)
        return f"GROUP BY {gi_str}"
    
    def tokens(self) -> List[str]:
        gi_str = [str(_) for _ in self._positionals] if self.is_positional \
            else [_.unindented_sql() for _ in self._expressions]
        gi_str = ', '.join(gi_str)
        return ['GROUP BY', gi_str]

class OrderByClauseExpression(ClauseExpression):

    def __init__(self, *ordering_items: SelectableExpressionType | Tuple[SelectableExpressionType, OrderBySpecExpression] | int):
        ordering_items = list(ordering_items)
        all_ints = all([isinstance(_, int) for _ in ordering_items])
        all_expressions_or_tuples = all([isinstance(_, (tuple, *self.allowed_expression_types())) for _ in ordering_items])
        if not (all_ints or all_expressions_or_tuples):
            raise TypeError("input can be either list of ints or a list with arguments that are either SelectableExpressionType or Tuple[SelectableExpressionType, OrderBySpecExpression]")
        
        if all_ints:
            self.is_positional = True
            if not all([_ > 0 for _ in ordering_items]):
                raise TypeError("can't have non-positive positional ordering items")
            if len(ordering_items) != len(set(ordering_items)):
                raise TypeError("duplicate ordering items")
            self._positionals = ordering_items
        else:
            self.is_positional = False
            self._expressions = []
            for arg in ordering_items:
                if isinstance(arg, self.allowed_expression_types()):
                    self._expressions.append((arg, OrderBySpecExpression()))
                elif isinstance(arg, tuple):
                    assert len(arg) == 2
                    expr, orderbyspec = arg
                    assert isinstance(expr, self.allowed_expression_types())
                    assert isinstance(orderbyspec, OrderBySpecExpression)
                    self._expressions.append((expr, orderbyspec))
                else:
                    TypeError()
            _keys = [_[0] for _ in self._expressions]
            if len(_keys) != len(set(_keys)):
                raise TypeError("duplicate ordering items")


    @staticmethod
    def allowed_expression_types():
        return tuple([
            LiteralExpression,
            ColumnExpression, 
            NullExpression, 
            LogicalOperationExpression, 
            MathOperationExpression, 
            CaseExpression])
    
    def resolve_positional_sql(self) -> str:
            return ', '.join([str(_) for _ in self._positionals])

        
    def resolve_expression_sql(self) -> str:
        result = []
        for expr, orderbyspec in self._expressions:
            result.append(f"{expr.unindented_sql()} {orderbyspec.unindented_sql()}")
        return ', '.join(result)
    
    def unindented_sql(self) -> str:
        items_str = self.resolve_positional_sql() if self.is_positional \
            else self.resolve_expression_sql()
        return f"ORDER BY {items_str}"
    
    def tokens(self) -> List[str]:
        items_str = self.resolve_positional_sql() if self.is_positional \
            else self.resolve_expression_sql()
        return ['ORDER BY', items_str]


class LimitClauseExpression(ClauseExpression):

    def __init__(self, limit: int, offset: Optional[int]=None):
        assert limit > 0 and isinstance(limit, int)
        if offset is not None:
            assert offset > 0 and isinstance(offset, int)
        self.limit = limit
        self.offset = offset

    def unindented_sql(self) -> str:
        _offset = "" if self.offset is None else f" OFFSET {self.offset}"
        return f"LIMIT {self.limit}{_offset}"
    
    def tokens(self) -> List[str]:
        _offset = "" if self.offset is None else f" OFFSET {self.offset}"
        return ['LIMIT', f"{self.limit}{_offset}"]
