from __future__ import annotations

from typing import Tuple
from sparkit.expression.base import *
from sparkit.expression.function import *
from sparkit.expression.operator import *

_function_expressions = SQLFunctionExpressions()

class Column:
    """A container for SQL expressions in Frames
    
    A column is not necessarily a materialized column in a table, 
    it can be any expression that is used for 
        SELECT
        WHERE, ON, HAVING, QUALIFY
        GROUP BY, ORDER BY
        and WINDOW clauses

    Initialization:
    It is recomeded not to use __init__ directly, rather use:
      functions.col
      function.lit (for literals)
      functions.when for CASE WHEN expressions

    Usage:
        - using arithmetic operations:
        >>> hours: Column = col("hours")
        >>> minutes: Column = hours * 60

        >>> price = lit("price")
        >>> discount = col("discout")
        >>> discounted_price = price - discount
        >>> discout_percent = discount / price

        - create boolean conditions:
        >>> qualifies = (col("age") > 18) and (col("grade") > 75)
        >>> has_address = col("address").is_not_null()

        - create CASE WHEN expressions
        >>> mycol = when(col("age") > 18, "over 18").when()

        aliases:
        >>> mycol = col("user_id").as_("id")
        >>> print(mycol.alias)
        id
    """

    @classmethod
    def allowed_expressions(cls) -> Tuple[Expression]:
        return (
            ColumnExpression, 
            LiteralExpression, 
            NullExpression, 
            CaseExpression,
            AbstractOperationExpression, 
            AbstractFunctionExpression, 
            NegatedExpression,
            AnalyticFunctionExpression)

    def __init__(self, **kwargs: str | Tuple[str, str] | Expression | Tuple[Expression, str]):
        """it is recommended to use the functions.col/lit/when methods to initialize Column 
        and to avoid the complex use of Expressions.
        
        There are 8 modes of initilization (2x2x2):
        either:
            name: str - a name of a physical column
        or:
            expression: Expression object of these types (and descendants): 
                ColumnExpression, LiteralExpression, NullExpression, 
                AbstractOperationExpression, AbstractFunctionExpression, NegatedExpression 

        The user can include an optional alias: str.
        The user can include an optional OrderBySpecExpression.


        Examples:
            recommended API:
            >>> from sqlkit.sql import col, lit
            >>> age = col("age")
            >>> age_plus_5 = age + lit(5)

            get columns from a Frame object:
            >>> from sqlkit.sql import table
            >>> payments: Frame = 

            
            to initialize directly from a str that represents a physical column name:
            >>> c = Column(name="user_id")

            or with a pointer to a table
            >>> c = Column(name="table1.user_id")

            including an alias
            >>> c = Column(name="user_id", alias="id")

            including an alias via the as_ method
            >>> c = Column(name="user_id")
            >>> c = c.as_("id")

            initializing using an expression
            >>> c = Column(expression=LiteralExpression(42))
            >>> c = Column(expression=LiteralExpression(42), alias="age")

            
        """
        # init
        self._alias = None
        self.expr = None
        self.order_by_spec = None
        
        kws = list(kwargs.keys())
        match kws:
            case ['name']:
                return Column.__init__(self, name=kwargs['name'], alias=None, order_by_spec=OrderBySpecExpression())
            case ['name', 'alias']:
                return Column.__init__(self, expression=ColumnExpression(kwargs['name']), alias=kwargs['alias'], order_by_spec=OrderBySpecExpression())
            case ['name', 'alias', 'order_by_spec']:
                return Column.__init__(self, expression=ColumnExpression(kwargs['name']), alias=kwargs['alias'], order_by_spec=kwargs['order_by_spec'])
            case ['expression']:
                return Column.__init__(self, expression=kwargs['expression'], alias=None, order_by_spec=OrderBySpecExpression())
            case ['expression', 'alias']:
                return Column.__init__(self, expression=kwargs['expression'], alias=kwargs['alias'], order_by_spec=OrderBySpecExpression())
            case ['expression', 'alias', 'order_by_spec']:
                match kwargs['expression']:
                    case Expression():
                        expr = kwargs['expression']
                        if not isinstance(expr, Column.allowed_expressions()):
                            raise TypeError(f"supported expression types are: {Column.allowed_expressions()}, got {type(expr)}")
                        else:
                            self.expr = kwargs['expression']
                    case _:
                        raise TypeError(f"expression needs to be an Expression type, got {type(expr)}")
                match kwargs['alias']:
                    case None:
                        pass
                    case str(alias):
                        self._alias = ValidName(alias)
                    case _:
                        raise TypeError(f"alias must be str, got {type(alias)}")
                match kwargs['order_by_spec']:
                    case OrderBySpecExpression():
                        self.order_by_spec = kwargs['order_by_spec']
                    case _:
                        raise TypeError(f"order_by_spec must of type OrderBySpecExpression, got {type(kwargs['order_by_spec'])}")
            case _:
                raise TypeError(f"expected keywords are either: name, (name, alias), expression or (expression, alias). Got {kws}")

    def __repr__(self) -> str:
        return f'<Column(expr={self.expr}, alias={self.alias})>'

    @classmethod
    def _resolve_type(cls, s: str | int | float | bool | Column, allowed_primitives=str | int | float | bool) -> Column:
        if isinstance(s, allowed_primitives):
            return Column(expression=LiteralExpression(s), alias=None)
        elif isinstance(s, Column):
            return s
        else:
            raise TypeError(f"only supporting str | int | float | bool | Column, got {type(s)}")
        
    @property
    def alias(self) -> Optional[str]:
        return None if self._alias is None else self._alias.name
    
    def as_(self, value: str):
        """change the alias"""
        return Column(expression=self.expr, alias=value)
    
    def __eq__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Equal(self.expr, other.expr), alias=None)

    def __ne__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=NotEqual(self.expr, other.expr), alias=None)
    
    def __gt__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Greater(self.expr, other.expr), alias=None)
    
    def __ge__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=GreaterOrEqual(self.expr, other.expr), alias=None)
    
    def __lt__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Less(self.expr, other.expr), alias=None)
    
    def __le__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=LessOrEqual(self.expr, other.expr), alias=None)
    
    def is_null(self) -> Column:
        return Column(expression=IsNull(self.expr), alias=None)
    
    def is_not_null(self) -> Column:
        return Column(expression=IsNotNull(self.expr), alias=None)
    
    def between(self, 
                from_: str | int | float | bool | Column, 
                to: str | int | float | bool | Column) -> Column:
        from_ = self._resolve_type(from_)
        to = self._resolve_type(to)
        return Column(expression=Between(self.expr, from_.expr, to.expr), alias=None)
    
    def __and__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=And(self.expr, other.expr), alias=None)
    
    def __or__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Or(self.expr, other.expr), alias=None)
    
    def like(self, other: str | Column) -> Column:
        if not isinstance(other, str | Column):
            raise TypeError(f"like only supports str | Column, got {type(other)}")
        other = self._resolve_type(other)
        return Column(expression=Like(self.expr, other.expr), alias=None)
    
    def __neg__(self) -> Column:
        return Column(expression=NegatedExpression(self.expr), alias=None)
    
    def __add__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Plus(self.expr, other.expr), alias=None)
    
    def __sub__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Minus(self.expr, other.expr), alias=None)
    
    def __mul__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Multiply(self.expr, other.expr), alias=None)
    
    def __truediv__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        return Column(expression=Divide(self.expr, other.expr), alias=None)
    
    def __mod__(self, other: str | int | float | bool | Column) -> Column:
        other: Column = self._resolve_type(other)
        expr =  _function_expressions.FunctionExpressionMOD(X=self.expr, Y=other.expr)
        return Column(expression=expr, alias=None)
    
    def __floordiv__(self, other: str | int | float | bool | Column) -> Column:
        other = self._resolve_type(other)
        div_expr = Divide(self.expr, other.expr)
        floor_expr = _function_expressions.FunctionExpressionFLOOR(X=div_expr)
        return Column(expression=floor_expr, alias=None)
    
    def when(self, condition: Column, value: str | int | float | bool | Column) -> Column:
        """only works when the expr is a CaseExpression"""
        if isinstance(self.expr, CaseExpression):
            if not isinstance(condition.expr, LogicalOperationExpression):
                condition = condition.is_not_null()
            case_expr = self.expr.add(condition.expr, self._resolve_type(value).expr)
            return Column(expression=case_expr, alias=None)
        else:
            raise TypeError("can only work on columns which have a CaseExpression, use when")
        
    def otherwise(self, value: str | int | float | bool | Column) -> Column:
        """only works when the expr is a CaseExpression"""
        if isinstance(self.expr, CaseExpression):
            case_expr = self.expr.add_otherwise(self._resolve_type(value).expr)
            return Column(expression=case_expr, alias=None)
        else:
            raise TypeError("can only work on columns which have a CaseExpression, use when")

    def asc(self, nulls: Optional[str]=None) -> Column:
        """order by asc, if nulls is None, keeps whatever spec exists now"""
        nulls = nulls.upper()
        assert nulls in ("FIRST", "LAST") 
        new_spec = OrderBySpecExpression(asc=True, nulls=nulls if nulls is not None else self.order_by_spec.nulls)
        return Column(expression=self.expr, alias=self.alias, order_by_spec=new_spec)
    
    def desc(self, nulls: Optional[str]=None) -> Column:
        """order by desc, if nulls is None, keeps whatever spec exists now"""
        if nulls is not None:
            nulls = nulls.upper()
            assert nulls in ("FIRST", "LAST")
        new_spec = OrderBySpecExpression(asc=False, nulls=nulls if nulls is not None else self.order_by_spec.nulls)
        return Column(expression=self.expr, alias=self.alias, order_by_spec=new_spec)
    
    def over(self, window_spec: Optional[WindowSpec]=None) -> Column:
        if window_spec is None:
            window_spec = WindowSpec(_partition_by=None, _order_by=None, _window_frame_clause=None)
        new_expr = AnalyticFunctionExpression(self.expr, window_spec_expr=window_spec._to_expr())
        return Column(expression=new_expr, alias=None)


@dataclass
class WindowSpec:
    """Holds a window_specification object
    
    While the original definition is:
    window_specification:
        [ named_window ]
        [ PARTITION BY partition_expression [, ...] ]
        [ ORDER BY expression [ { ASC | DESC } ] [, ...] ]
        [ window_frame_clause ]

    Our implementation does not include name_window, as a WindoSpec object can be assigned to a variable and reused

    Arguments:
        _partition_by - optional list of Column
        _order by - optional list of Column
        _window_fram_clause - an optional object of WindowFrameClause
    
        
    Usage:
        It is recommended to use the methods and not the __init__ directly

    Source:
        https://cloud.google.com/bigquery/docs/reference/standard-sql/window-function-calls#def_window_spec
    
    
    """
    _partition_by: Optional[List[Column]]=None
    _order_by: Optional[List[Column]]=None
    _window_frame_clause: Optional[WindowFrameExpression]=None

    def __post_init__(self):
        if self._partition_by is not None:
            assert all([isinstance(col, Column) for col in self._partition_by])
        if self._order_by is not None:
            assert all([isinstance(col, Column) for col in self._order_by])
        if self._window_frame_clause is not None:
            assert isinstance(self._window_frame_clause, WindowFrameExpression)

    def partition_by(self, *cols: Column | str) -> WindowSpec:
        """replaces any existing 'partition by' definition"""
        cols = list(cols)
        all_col = all([isinstance(_, Column) for _ in cols])
        all_str = all([isinstance(_, str) for _ in cols])
        
        if not (all_col or all_str):
            raise TypeError("cols needs to be all Column or all str")
        if all_str:
            cols = [Column(expression=ColumnExpression(_)) for _ in cols]

        return WindowSpec(cols, self._order_by, self._window_frame_clause)
        
    def order_by(self, *cols: Column | str) -> WindowSpec:
        """replaces any existing 'order by' definition"""
        cols = list(cols)
        all_col = all([isinstance(_, Column) for _ in cols])
        all_str = all([isinstance(_, str) for _ in cols])
        
        if not (all_col or all_str):
            raise TypeError("cols needs to be all Column or all str")
        if all_str:
            cols = [Column(expression=ColumnExpression(_)) for _ in cols]
        
        return WindowSpec(self._partition_by, cols, self._window_frame_clause)
    
    def rows_between(self, start: Optional[int]=None, end: Optional[int]=0) -> WindowSpec:
        wfe = WindowFrameExpression(True, start, end)
        return WindowSpec(self._partition_by, self._order_by, wfe)

    def range_between(self, start: Optional[int]=None, end: Optional[int]=0) -> WindowSpec:
        wfe = WindowFrameExpression(False, start, end)
        return WindowSpec(self._partition_by, self._order_by, wfe)
    
    def _to_expr(self) -> WindowSpecExpression:
        """transform to a WindowSpecExpression"""
        partition_by = None
        order_by = None

        if self._partition_by is not None:
            partition_by = [col.expr for col in self._partition_by]
        if self._order_by is not None:
            order_by = [(_.expr, _.order_by_spec) for _ in self._order_by]

        return WindowSpecExpression(
            partition_by=partition_by, 
            order_by=order_by, 
            window_frame_clause=self._window_frame_clause)
