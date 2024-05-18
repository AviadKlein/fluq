from __future__ import annotations

from typing import Optional
from expression import *
from column import Column

def copy_doc(source, preamble: Optional[str]=None):
    """decorator to copy __doc__ str between methods"""
    def decorator(target):
        target.__doc__ = source.__doc__
        if preamble is not None:
            target.__doc__ = f"{preamble}\n\n{target.__doc__}"
        return target
    return decorator

class Frame:
    """The Frame API to writing SQL in a functional manner
    It is advised not to try and initialize a Frame directly, rather, one should use an exisiting frame
    or start from the 'table' method that points to a table and returns a default 'SELECT * FROM...' Frame object

    Examples:
        >>> frame: Frame = table("db.schema.t1").select("id", "name", "age")
    """

    def __init__(self, queryable_expression: QueryAble, alias: Optional[str]=None):
        assert isinstance(queryable_expression, QueryAble)
        self._query_expr = queryable_expression
        self._alias = None
        if alias is not None:
            self._alias = ValidName(alias)

    def as_(self, alias: str) -> Frame:
        assert isinstance(alias, str)
        return Frame(self._query_expr, alias)
    
    @property
    def alias(self) -> str:
        return self._alias.name if self._alias is not None else None
    
    @alias.setter
    def alias(self, value: str):
        raise SyntaxError("can't assign alias, use the as_ method instead")

    def _is_select_all(self) -> bool:
        if isinstance(self._query_expr, QueryExpression):
            return self._query_expr.select_clause.is_select_all()
        else:
            raise NotImplementedError()
    
    def select(self, *args: str | Column) -> Frame:
        """Select columns
        
        Args:
            either a series of str or a series of columns, types can't be mixed
        
        Returns:
            If the Frame is a just a pointer to a source with 'SELECT *', the select clause will be replaced
            Otherwise, the current query will be subqueried and the select will select from it
            In the latter case, the Frame needs to have an alias
        
        Raises:
            TypeError when args are not all str or all column

        Examples:
            >>> fc: Frame = table("db.schema.t1").select("id", "name", "age")
        """
        
        # type check
        args = list(args)
        type_check_str = all([isinstance(_, str) for _ in args])
        type_check_col = all([isinstance(_, Column) for _ in args])
        if not (type_check_str or type_check_col):
            raise TypeError("only *args as all str OR all Column is supported")
        
        # resolve select clause
        if len(args) == 1 and args[0] == "*":
            select_clause = SelectClauseExpression.wildcard()
        elif type_check_str:
            select_clause = SelectClauseExpression.from_args(*[(ColumnExpression(_), None) for _ in args])
        else:
            expressions = [_.expr for _ in args]
            aliases = [_.alias for _ in args if _.alias is not None]
            select_clause = SelectClauseExpression(expressions, aliases)
        
        # check if current select clause is '*'
        if self._is_select_all(): # if so, replace it
            return Frame(self._query_expr.copy(select_clause=select_clause))
        else: # otherwise, create a sub query
            assert self.alias is not None, "when sub selecting, first use an alias"
            sub_query = QueryExpression(
                from_clause=FromClauseExpression(query=self._query_expr, alias=self.alias),
                select_clause=select_clause
                )
            return Frame(sub_query)
    
    def where(self, predicate: Column) -> Frame:
        """Add/append a Where clause using a logical predicate

        Args:
            predicate (Column): any column object

        Returns:
            an updated Frame

        Raises:
            TypeError/Assertion error if the column is not instantiated correctly

        Examples:
            >>> fc: Frame = table("db.schema.t1").where(col("t1").equal(1))
            >>> print(fc.sql)
        """
        where_expr = predicate.expr
        if isinstance(self._query_expr, QueryExpression):
            if self._query_expr.where_clause is None:
                new_query = self._query_expr.copy(where_clause=WhereClauseExpression(where_expr))
            else:
                new_query = self._query_expr.copy(
                    where_clause=self._query_expr.where_clause.and_(where_expr)
                    )
            return Frame(new_query)
        else:
            raise NotImplementedError()

    def _is_simple(self) -> bool:
        if isinstance(self._query_expr, QueryExpression):
            return self._query_expr.is_simple()
        else:
            return False

    @copy_doc(where, preamble="An alias for 'where'")
    def filter(self, predicate: Column) -> Frame:
        return self.where(predicate=predicate)
    
    def join(self, other: Frame, on: Column, join_type: str='inner') -> Frame:
        """
        Joins a Frame with another
        both frames will be wrapped in a subquery and will require an alias, the select wil be 

        Args:
            other: Frame - the object to join
            on: Column - a predicate to join on
            join_type: str - 'inner' (default), 'left', 'right' or 'full other'

        Raises:
            TypeError/AssertionError on types and missing aliases

        Examples:
            >>> t1 = table("db.schema.t1").as_("t1")
            >>> t2 = table("db.schema.t2").as_("t2")
            >>> t3 = (
                    t1.join(t2, on=col("t1.id").eq(col("t2.id")))
                    .select("t1.id", "t2.name")
                )
            >>> print(t3.sql)
        """
        assert isinstance(other, Frame)
        assert isinstance(on, Column)
        assert isinstance(join_type, str) and join_type in ['inner', 'left', 'right', 'full outer']

        if self.alias is None:
            raise TypeError("alias needs to be defined before cartesian join")
        if other.alias is None:
            raise TypeError("other's alias needs to be defined before cartesian join")

        match (self._is_simple(), other._is_simple()):
            case (True, True):
                this: QueryExpression = self._query_expr # only QueryExpression can be simple
                that: QueryExpression = other._query_expr
                this_table: TableNameExpression = this.from_clause.from_item
                that_table: TableNameExpression = that.from_clause.from_item
                assert (self.alias is not None) and (other.alias is not None), \
                    f"both aliases need to be defined"
                kwargs = {
                    'left': this_table, 'right': that_table,
                    'left_alias': self.alias, 'right_alias': other.alias,
                    'on': on.expr
                }
                join_expression = JoinOperationExpression.from_kwargs(join_type=join_type, **kwargs)
            case _:
                join_expression = JoinOperationExpression.from_kwargs(
                    join_type=join_type,
                    left=self._query_expr, right=other._query_expr,
                    left_alias=self.alias, right_alias=other.alias,
                    on=on.expr
                )
        select_clause = SelectClauseExpression.from_args(ColumnExpression("*"))
        from_clause = FromClauseExpression(join_expression=join_expression)
        query = QueryExpression(from_clause=from_clause, select_clause=select_clause)
        return Frame(queryable_expression=query)
        
    def cartesian(self, other: Frame) -> Frame:
        """
        performs a cartesian (cross join) with another frame
        both frames will be wrapped in a subquery and will require an alias, the select will be simple

        Args:
            other: Frame - the object to join
            join_type: str - 'inner' (default), 'left', 'right' or 'full other'

        Raises:
            TypeError/AssertionError on types and missing aliases

        Examples:
            >>> t1 = table("db.schema.t1").as_("t1")
            >>> t2 = table("db.schema.t2").as_("t2")
            >>> t3 = t1.cartesian(t2).select("t1.id", "t2.name")
            >>> print(t3.sql)
        """
        assert isinstance(other, Frame)

        if self.alias is None:
            raise TypeError("alias needs to be defined before cartesian join")
        if other.alias is None:
            raise TypeError("other's alias needs to be defined before cartesian join")
        
        match (self._is_simple(), other._is_simple()):
            case (True, True):
                this: QueryExpression = self._query_expr # only QueryExpression can be simple
                that: QueryExpression = other._query_expr
                this_table: TableNameExpression = this.from_clause.from_item
                that_table: TableNameExpression = that.from_clause.from_item
                assert (self.alias is not None) and (other.alias is not None), \
                    f"both aliases need to be defined"
                kwargs = {
                    'left': this_table, 'right': that_table,
                    'left_alias': self.alias, 'right_alias': other.alias,
                }
                join_expression = JoinOperationExpression.from_kwargs(join_type='cross', **kwargs)
            case _:
                join_expression = JoinOperationExpression.from_kwargs(
                    join_type='cross', left=self._query_expr, right=other._query_expr,
                    left_alias=self.alias, right_alias=other.alias
                )
        select_clause = SelectClauseExpression.wildcard()
        from_clause = FromClauseExpression(join_expression=join_expression)
        query = QueryExpression(from_clause=from_clause, select_clause=select_clause)
        return Frame(queryable_expression=query)
    
    @copy_doc(cartesian, preamble="An alias for 'cartesian'")
    def cross_join(self, other: Frame) -> Frame:
        return self.cartesian(other)

    def group_by(self, *args: str | Column | int) -> GroupByFrame:
        # args = list()
        # all_str = all([isinstance(_, str) for _ in args])
        # all_col = all([isinstance(_, Column) for _ in args])
        # all_int = all([isinstance(_, int) for _ in args])
        # if not (all_str or all_col or all_int):
        #     raise TypeError("args need to be either all str, all Column or all int")
        # if all_col:
        #     args = [_.expr for _ in args]
        # if all_str:
        #     args = [ColumnExpression(_) for _ in args]

        # group_by_clause = GroupByClauseExpression(*args)
        raise NotImplementedError()
   
    def with_column(self, alias: str, col: Column) -> Frame:
        """
        Add another column to the select clause by wrpping the query in a subselect
        If the new col name is X, will result in:
            SELECT _t1.*, <col> AS X FROM (<sub query>) as _t1

        Args:
            alias: str - the name for the new column
            col: Column - any Column object

        Raises:
            AssertionError on types

        Examples:
            >>> t = table("db.schema.t1").as_("t1").withColumn("depositor", col("deposits").gt(0))
        """
        assert isinstance(col, Column)
        col = col.as_(alias)
        select_clause = SelectClauseExpression.from_args(ColumnExpression("*"), (col.expr, col.alias))
        from_clause = FromClauseExpression(self._query_expr, alias="_t1")
        query = QueryExpression(from_clause=from_clause, select_clause=select_clause)
        return Frame(queryable_expression=query)

    def limit(self, limit: int, offset: Optional[int] = None) -> Frame:
        """
        Add/Updates a Limit clause to the query
        """
        raise NotImplementedError()

    def order_by(self, *args) -> Frame:
        raise NotImplementedError()

    def union(self, other: Frame) -> Frame:
        raise NotImplementedError()

    def intersect(self, other: Frame) -> Frame:
        raise NotImplementedError()

    @property
    def sql(self) -> str:
        return self._query_expr.sql
    
class GroupByFrame:

    def __init__(self) -> None:
        pass

    def agg(self, *args) -> Frame:
        raise NotImplementedError()

def table(db_path: str) -> Frame:
    from_clause = FromClauseExpression(table=TableNameExpression(db_path))
    select_clause = SelectClauseExpression.from_args(ColumnExpression("*"))
    query = QueryExpression(from_clause=from_clause, select_clause=select_clause)
    return Frame(queryable_expression=query)

