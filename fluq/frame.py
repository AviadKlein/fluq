from __future__ import annotations

from typing import Optional
from fluq.expression.base import *
from fluq.expression.query import QueryableExpression, QueryExpression
from fluq.expression.clause import *
from fluq.expression.join import *
from fluq.expression.selectable import ColumnExpression
from fluq.expression.set_operation import *
from fluq.column import Column
from fluq.render import Renderable


def _copy_doc(source, preamble: Optional[str]=None):
    """decorator to copy __doc__ str between methods"""
    def decorator(target):
        target.__doc__ = source.__doc__
        if preamble is not None:
            target.__doc__ = f"{preamble}\n\n{target.__doc__}"
        return target
    return decorator

class Frame(ResultSet):
    """The Frame API to writing SQL in a functional manner
    It is advised not to try and initialize a Frame directly, rather, one should use an exisiting frame
    or start from the 'table' method that points to a table and returns a default 'SELECT * FROM...' Frame object

    Examples:
        >>> frame: Frame = table("db.schema.t1").select("id", "name", "age")
    """

    def __init__(self, queryable_expression: QueryableExpression, alias: Optional[str]=None):
        assert isinstance(queryable_expression, QueryableExpression)
        self._query_expr = queryable_expression
        self._alias = None
        if alias is not None:
            self._alias = ValidName(alias)
        # if the user did not supply an alias, we try to infer it from the query
        else:
            match self._query_expr:
                case QueryExpression(_) if self._query_expr.from_clause is None:
                    pass
                case QueryExpression(_):
                    match self._query_expr.from_clause.from_item, self._query_expr.from_clause.alias:
                        case TableNameExpression(db_path), None:
                            self._alias = ValidName(db_path.last_identifer())
                        case TableNameExpression(_), str(name):
                            self._alias = ValidName(name)
                        case _:
                            pass
                case _:
                    pass

    def as_(self, alias: str) -> Frame:
        assert isinstance(alias, str)
        return Frame(self._query_expr, alias)
    
    def _get_expr(self) -> Expression:
        return self._query_expr
    
    @property
    def alias(self) -> Optional[str]:
        return self._alias.name if self._alias is not None else None
    
    @alias.setter
    def alias(self, value: str):
        raise SyntaxError("can't assign alias, use the as_ method instead")

    def _is_select_all(self) -> bool:
        if isinstance(self._query_expr, QueryExpression):
            return self._query_expr.select_clause.is_select_all()
        else:
            raise NotImplementedError()
        
    def __call__(self, col: str) -> Column:
        """an api into columns of the Frame
        
        Arguments:
            col: str - a valid column name

        Usage:
            >>> payments = table("db.schema.payments")
            >>> id: Column = payments("id")

            if the Frame has an alias, it too will be passed to the Column identifer
            >>> payments = table("db.schema.payments").as_("p")
            >>> id: Column = payments("id")
            >>> print(id.alias)
                p

            >>> payments = table("db.schema.payments")
            >>> query = payments.group_by(payments("id")).agg(sum("value"))
            >>> print(query.sql)
                SELECT id, SUM(value)
                FROM db.schema.payments
                GROUP BY id
        """
        identifier = col if self.alias is None else f"{self.alias}.{col}"
        return Column(expression=ColumnExpression(identifier), alias=None)
    
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
        if type_check_str:
            select_clause = SelectClauseExpression.from_args(*[(ColumnExpression(_), None) for _ in args])
        else:
            expressions = [_.expr for _ in args]
            aliases = [_.alias for _ in args]
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

    @_copy_doc(where, preamble="An alias for 'where'")
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
        
    def cartesian(self, other: Frame | Column) -> Frame:
        """
        performs a cartesian (cross join) with another frame or "special" columns (see below)
        both frames will be wrapped in a subquery and will require an alias, the select will be simple

        Args:
            other: Frame | Column - the object to join
                no restrictions for any kind of Frame
                Column, however, needs to be an UNNESTed column, see examples
            join_type: str - 'inner' (default), 'left', 'right' or 'full other'

        Raises:
            TypeError/AssertionError on types and missing aliases

        Examples:
            >>> t1 = table("db.schema.t1").as_("t1")
            >>> t2 = table("db.schema.t2").as_("t2")
            >>> t3 = t1.cartesian(t2).select("t1.id", "t2.name")
            >>> print(t3.sql)

            Using UNNEST:
            >>> table("db.schema.t1").as_("t1").cartesian(unnest(array(1,2,3)).as_("arr"))
        """
        assert isinstance(other, Frame | Column)
            

        if self.alias is None:
            raise TypeError("alias needs to be defined before cartesian join")
        if other.alias is None:
            raise TypeError("other's alias needs to be defined before cartesian join")
        
        if isinstance(other, Column):
            if not isinstance(other.expr, UnNestOperatorExpression):
                raise SyntaxError("can't join on a column that is not an UNNEST operator")
            match self._is_simple():
                case False:
                    join_expression = JoinOperationExpression.from_kwargs(
                        join_type='cross',
                        left=self._query_expr, 
                        left_alias=self.alias, 
                        right=other.expr, 
                        right_alias=other.alias
                    )
                case True:
                    this: QueryExpression = self._query_expr
                    join_expression = JoinOperationExpression.from_kwargs(
                        join_type='cross',
                        left=this.from_clause.from_item, 
                        left_alias=self.alias, 
                        right=other.expr, 
                        right_alias=other.alias
                    )

        else:
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
    
    @_copy_doc(cartesian, preamble="An alias for 'cartesian'")
    def cross_join(self, other: Frame) -> Frame:
        return self.cartesian(other)

    def group_by(self, *cols: Column) -> GroupByFrame:
        return GroupByFrame(
            query=self._query_expr, 
            alias=self.alias, 
            grouping_items=list(cols))
   
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
        if not isinstance(limit, int):
            raise TypeError(f"limit must be int, got {type(limit)}")
        if offset is not None:
            if not isinstance(offset, int):
                raise TypeError(f"offset, if defined, must be int, got {type(offset)}")
        limit_clause = LimitClauseExpression(limit=limit, offset=offset)
        new_query = None
        match self._query_expr:
            case QueryExpression():
                new_query = self._query_expr.copy(limit_clause=limit_clause)
                return Frame(new_query)
            case QueryableExpression():
                raise NotImplementedError()

    def order_by(self, *cols: str | Column) -> Frame:
        """Will replace any order by clause that exists"""
        cols = list(cols)
        all_str = all([isinstance(_, str) for _ in cols])
        all_col = all([isinstance(_, Column) for _ in cols])
        if not (all_col or all_str):
            raise TypeError("args must be all str or all Column")
        if all_str:
            cols = [Column(name=_) for _ in cols]
        expr_and_specs = []
        for col in cols:
                expr_and_specs.append((col.expr, col.order_by_spec))
        order_by_clause = OrderByClauseExpression(*expr_and_specs)
        new_query = None
        match self._query_expr:
            case QueryExpression():
                new_query = self._query_expr.copy(order_by_clause=order_by_clause)
                return Frame(new_query, alias=self.alias)
            case QueryableExpression():
                raise NotImplementedError()

    def _set_operation(self, other: Frame, operation: SetOperation):
        left = self._query_expr
        right = other._query_expr
        set_operation = operation(left=left, right=right)
        return Frame(queryable_expression=set_operation)

    def union_all(self, other: Frame) -> Frame:
        return self._set_operation(other=other, operation=UnionAllSetOperation)
    
    def union_distinct(self, other: Frame) -> Frame:
        return self._set_operation(other=other, operation=UnionDistinctSetOperation)

    def intersect_distinct(self, other: Frame) -> Frame:
        return self._set_operation(other=other, operation=IntersectSetOperation)
    
    def except_distinct(self, other: Frame) -> Frame:
        return self._set_operation(other=other, operation=ExceptSetOperation)
    
    def distinct(self) -> Frame:
        """return a DISTINCT sql query
        
        Behavior:
         if the internal query is a simple one, will just append the DISTINCT keyword to the select clause
         if the internal query is a set operation, will wrap the entire query as a sub-query and will SELECT DISTINCT * from it"""
        match self._query_expr:
            case QueryExpression(_):
                new_select_clause = self._query_expr.select_clause.distinct()
                new_expr = self._query_expr.copy(select_clause=new_select_clause)
                return Frame(queryable_expression=new_expr, alias=self.alias)
            case SetOperation(_):
                "wrap as a subselect"
                if self.alias is None:
                    raise SyntaxError("querying over set operations requires an alias")
                new_select_clause = SelectClauseExpression.wildcard().distinct()
                new_from_clause = FromClauseExpression(query=self._query_expr, alias=self.alias)
                new_query_expr = QueryExpression(from_clause=new_from_clause, select_clause=new_select_clause)
                return Frame(queryable_expression=new_query_expr, alias=None)
            case _:
                raise TypeError(f"unsupported Querayble, got {type(self._query_expr)}")
        
    @property
    def sql(self) -> Renderable:
        return self._query_expr.sql

    def source_table_names(self) -> List[str]:
        exprs = self._get_expr().filter(predicate=lambda e: isinstance(e, TableNameExpression))
        return list(map(lambda e: e.db_path.name, exprs))

class GroupByFrame:

    def __init__(self, query: QueryExpression, alias: Optional[str], grouping_items: List[Column]):
        # type checks
        if not isinstance(query, QueryExpression):
            raise TypeError(f"query must be QueryExpression, got {type(query)=}")
        
        if not all([isinstance(_, Column) for _ in grouping_items]):
            raise TypeError("GroupByFrame only supports Column(s)")

        # resolve expressions and aliases
        self.query = query
        self.alias = alias
        self.group_by_expr = [_.expr for _ in grouping_items]
        self.group_by_aliases = [_.alias for _ in grouping_items]
    
    def _resolve_expressions_and_aliases(self, *cols: Column) -> List[Tuple[Expression, Optional[str]]]:
        """returns a list of tuples
        the first elements in the list are the group by expr and their optional aliases
        the last elements in the list are the agg exper and their optional aliases
        """
        cols = list(cols)
        if len(cols) == 0:
            raise TypeError("args can't be empty")
        if not all([isinstance(_, Column) for _ in cols]):
            raise TypeError("only Column type is allowed in GroupByFrame.agg")
        # concat group_by_expr, agg_expr and their aliases
        select_expr = [_.expr for _ in cols]
        select_aliases = [_.alias for _ in cols]
        return list(zip(self.group_by_expr, self.group_by_aliases)) + list(zip(select_expr, select_aliases))
   
    def agg(self, *cols: Column) -> Frame:
        zipped = self._resolve_expressions_and_aliases(*cols)
        
        select_clause = SelectClauseExpression.from_args(*zipped)
        group_by_clause = GroupByClauseExpression(*self.group_by_expr)

        match self.query:
            case QueryExpression(None, _, _, _, _, _, _):
                raise SyntaxError("can't group by a QueryExpression that has no From clause, use the table method to create a Frame first")
            case QueryExpression() if self.query.is_simple():
                new_query = QueryExpression(
                    from_clause=self.query.from_clause, 
                    select_clause=select_clause,
                    group_by_clause=group_by_clause)
            case _:
                if self.alias is None:
                    raise SyntaxError("frame requires an alias before group_by")
                new_query = QueryExpression(
                    from_clause=FromClauseExpression(query=self.query, alias=self.alias),
                    select_clause=select_clause,
                    group_by_clause=group_by_clause
                )
        return Frame(queryable_expression=new_query)

