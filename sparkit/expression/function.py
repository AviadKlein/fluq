from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from abc import abstractmethod

from sparkit.expression.base import *
from sparkit.expression.operator import *


# Selectable types
SelectableExpressionType = LiteralExpression | ColumnExpression | \
    LogicalOperationExpression | MathOperationExpression | NullExpression

@dataclass
class WindowFrameExpression(Expression):
    """Window frames
    
    Source:
        https://cloud.google.com/bigquery/docs/reference/standard-sql/window-function-calls#def_window_frame
    
    A window frame can be either rows or range
    Both require an order by spec in the WindowSpec
    If range is selected, only 1 expression can be included in the order_by spec
    and it must be numeric (not inforced by this package)

    If start is UNBOUNDED PRECEDING then end can be either:
        X PRECEDING, CURRENT ROW, Z FOLLOWING, UNBOUNDED FOLLOWING
    If start is Y PRECEDING then end can be either:
        X PRECEDING, CURRENT ROW, Z FOLLOWING, UNBOUNDED FOLLOWING
        such that Y > X
    If start is CURRENT ROW then end can be either:
        CURRENT ROW, Z FOLLOWING, UNBOUNDED FOLLOWING
    If start is X FOLLOWING then end can be either:
        Z FOLLOWING, UNBOUNDED FOLLOWING
        such that Z > X

    To implement this logic, we will use:
      None - to indicated 'unboundness'
      start = None --> UNBOUNDED PRECEDING
      end = None --> UNBOUNDED FOLLOWING
      negative numbers will depict preceding and positive will depict following

      start will have to be leq than end
    
    Usage:
        TODO
    """
    rows: bool=True
    start: Optional[int]=None
    end: Optional[int]=0

    def __post_init__(self):
        if not isinstance(self.rows, bool):
            raise 
        match self.start, self.end:
            case None, None:
                pass
            case int(_), None:
                pass
            case None, int(_):
                pass
            case int(start), int(end):
                if start > end:
                    raise TypeError("start must be smaller than end")
            case start, end:
                raise TypeError(f"start, end must be ints, got {type(start)=} and {type(end)=}")
        
    
    def unindented_sql(self) -> str:
        rows_range = "ROWS" if self.rows else "RANGE"
        between = [None, None]
        match self.start:
            case None:
                between[0] = 'UNBOUNDED PRECEDING'
            case 0:
                between[0] = 'CURRENT ROW'
            case s:
                between[0] = f"{abs(s)} {'PRECEDING' if s < 0 else 'FOLLOWING'}"
        match self.end:
            case None:
                between[1] = 'UNBOUNDED FOLLOWING'
            case 0:
                between[1] = 'CURRENT ROW'
            case e:
                between[1] = f"{abs(e)} {'PRECEDING' if e < 0 else 'FOLLOWING'}"
        return f"{rows_range} BETWEEN {between[0]} AND {between[1]}"

@dataclass
class WindowSpecExpression(Expression):
    partition_by: Optional[List[SelectableExpressionType]]=None
    order_by: Optional[List[Tuple[SelectableExpressionType, Optional[OrderBySpecExpression]]]]=None
    window_frame_clause: Optional[WindowFrameExpression]=None

    def __post_init__(self):
        if self.partition_by is not None:
            assert all([isinstance(_, SelectableExpressionType) for _ in self.partition_by])
        if self.order_by is not None:
            assert all([isinstance(_[0], SelectableExpressionType) for _ in self.order_by])
            assert all([isinstance(_[1], OrderBySpecExpression) for _ in self.order_by if _[1] is not None])
        if self.window_frame_clause is not None:
            assert isinstance(self.window_frame_clause, WindowFrameExpression)

        match self:
            case WindowSpecExpression(part, None, spec) if spec is not None:
                raise SyntaxError("If a WindowFrameExpression is defined in a WindowSpecExpression, and order_by object needs to be defined as well")
            case WindowSpecExpression(_, order, WindowFrameExpression(False, _, _)) if len(order) > 1:
                raise SyntaxError(f"RANGE allows only 1 numeric column, got {len(order)}")
    
    def unindented_sql(self) -> str:
        result = []
        match self:
            case WindowSpecExpression(part, ord, spec):
                match part:
                    case None:
                        pass
                    case list(_):
                        result.append(f"PARTITION BY {', '.join([_.unindented_sql() for _ in part])}")
                match ord:
                    case None:
                        pass
                    case list(_):
                        ord_result = []
                        for expr, order_by_spec in ord:
                            curr = expr.unindented_sql()
                            if order_by_spec is not None:
                                curr += f" {order_by_spec.unindented_sql()}"
                            ord_result.append(curr)
                        result.append(f"ORDER BY {', '.join(ord_result)}")
                match spec:
                    case None:
                        pass
                    case WindowFrameExpression(_):
                        result.append(spec.unindented_sql())
        return ' '.join(result)

@dataclass
class AnalyticFunctionExpression(Expression):
    expr: SelectableExpressionType
    window_spec_expr: WindowSpecExpression

    def unindented_sql(self) -> str:
        return f"{self.expr.unindented_sql()} OVER({self.window_spec_expr.unindented_sql()})"
    
    # Functions
class AbstractFunctionExpression(Expression):
    """abstract method to hold all function expressions

    functions, as expressions, are just a symbol and a list of named arguments
    all functions are created dynamically and are stored within SQLFunctions

    the naming convention is to use the 'symbol' method as the name for the function
    """
    
    @abstractmethod
    def arguments_by_order(self) -> List[str]:
        pass

    @abstractmethod
    def symbol(self) -> str:
        pass

    @abstractmethod
    def is_aggregate(self) -> bool:
        pass

    def validate_arguments(self, **kwargs) -> Dict[str, Expression]:
        expected_args = self.arguments_by_order()
        keys = list(kwargs.keys())

        cond = len(keys) == len(expected_args)
        cond &= all([e==a for e,a in zip(expected_args, keys)])
        if not cond:
            unrecognized_args = []
            bad_values = {}
            
            missing_args = [_ for _ in expected_args if _ not in keys]
            for key, value in kwargs:
                if key not in expected_args:
                    unrecognized_args.append(key)
                if not isinstance(value, Expression):
                    bad_values[key] = value

            if len(unrecognized_args) > 0:
                raise TypeError(f"function {self.symbol()} got unrecognized args: {unrecognized_args}")
            if len(missing_args) > 0:
                raise TypeError(f"function {self.symbol()} is missing args: {missing_args}")
            if len(bad_values) > 0:
                raise TypeError(f"function {self.symbol()} expects Expression as values, got {[(k, type(v)) for k, v in bad_values]}")
        else:
            return kwargs

    def __init__(self, **kwargs) -> None:
        self.kwargs = self.validate_arguments(**kwargs)
        
    def unindented_sql(self) -> str:
        args: str = ', '.join([_.sql for _ in self.kwargs.values()])
        return f"{self.symbol()}({args})"
    

class SQLFunctionExpressions:

    @classmethod
    def _params(cls):
        return [
            ("MOD", ["X", "Y"], False),
            ("FLOOR", ["X"], False),
            ("CURRENT_DATE", [], False),
            ("SUM", ["X"], True),
            ("COUNT", ["X"], True),
            ("MAX", ["X"], True),
            ("MIN", ["X"], True),
            ("AVG", ["X"], True),
            ("ANY_VALUE", ["X"], True),
        ]
    
    @classmethod
    def create_concrete_expression_class(cls, symbol: str, arguments: List[str], is_aggregate: bool):

        def symbol_creator(self):
            return symbol
        
        def arguments_creator(self):
            return arguments
        
        def is_aggregate_creator(self):
            return is_aggregate
        
        return type(
            symbol, 
            (AbstractFunctionExpression, ), 
            {
                'symbol': symbol_creator, 
                'arguments_by_order': arguments_creator,
                'is_aggregate': is_aggregate_creator}
            )

    def __init__(self) -> None:
        for symbol, arguments, is_aggregate in self._params():
            setattr(self, f"FunctionExpression{symbol}", self.create_concrete_expression_class(symbol, arguments, is_aggregate))
    

class CaseExpression(Expression):

    @classmethod
    def _resolve_condition(cls, condition: Expression) -> LogicalOperationExpression:
        if isinstance(condition, LogicalOperationExpression):
            return condition
        else:
            return condition.to_logical()

    def __init__(self, cases: List[Tuple[Expression, Expression]], otherwise: Optional[Expression]=None):
        self.cases = [(self._resolve_condition(condition), value) for condition, value in cases]
        self.otherwise = otherwise

    def add(self, condition: Expression, value: Expression) -> CaseExpression:
        new_cases = [*self.cases, (self._resolve_condition(condition), value)]
        return CaseExpression(new_cases, self.otherwise)

    def add_otherwise(self, otherwise: Expression) -> CaseExpression:
        return CaseExpression(self.cases, otherwise)

    @classmethod
    def _case_to_sql(cls, operation: Expression, expr: Expression) -> str:
        return f"WHEN {operation.unindented_sql()} THEN {expr.unindented_sql()}"
    
    def cases_unindented_sql(self) -> List[str]:
        cases = [self._case_to_sql(operation, expr) for operation, expr in self.cases]
        otherwise = [] if self.otherwise is None else [f"ELSE {self.otherwise.unindented_sql()}"]
        return cases + otherwise
    
    def unindented_sql(self) -> str:
        return self.sql(indent = Indent())
        
    @property
    def sql(self, indent: Indent = Indent()) -> str:
        if len(self.cases) == 0:
            raise ValueError("can't render to sql with 0 cases")
        cases = self.cases_unindented_sql()
        cases = [f"{indent.plus1()}{case}" for case in cases]
        cases = '\n'.join(cases)
        return f"{indent}CASE\n{cases}\n{indent}END"     

