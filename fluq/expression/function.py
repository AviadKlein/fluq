from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
from abc import abstractmethod

from fluq.expression.base import *
from fluq.expression.base import Expression
from fluq.expression.literals import OrderBySpecExpression
from fluq.expression.operator import *


@dataclass
class WindowFrameExpression(TerminalExpression):
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
    
    def tokens(self) -> List[str]:
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
        return [rows_range, 'BETWEEN', between[0], 'AND', between[1]]

@dataclass
class WindowSpecExpression(Expression):
    partition_by: Optional[List[SelectableExpression]]=None
    order_by: Optional[List[Tuple[SelectableExpression, Optional[OrderBySpecExpression]]]]=None
    window_frame_clause: Optional[WindowFrameExpression]=None

    def __post_init__(self):
        if self.partition_by is not None:
            assert all([isinstance(_, SelectableExpression) for _ in self.partition_by])
        if self.order_by is not None:
            assert all([isinstance(_[0], SelectableExpression) for _ in self.order_by])
            assert all([isinstance(_[1], OrderBySpecExpression) for _ in self.order_by if _[1] is not None])
        if self.window_frame_clause is not None:
            assert isinstance(self.window_frame_clause, WindowFrameExpression)

        match self:
            case WindowSpecExpression(part, None, spec) if spec is not None:
                raise SyntaxError("If a WindowFrameExpression is defined in a WindowSpecExpression, and order_by object needs to be defined as well")
            case WindowSpecExpression(_, order, WindowFrameExpression(False, _, _)) if len(order) > 1:
                raise SyntaxError(f"RANGE allows only 1 numeric column, got {len(order)}")
    
    def tokens(self) -> List[str]:
        result = []
        match self:
            case WindowSpecExpression(part, ord, spec):
                match part:
                    case None:
                        pass
                    case list(_):
                        head, *tail = part
                        part = head.tokens()
                        for elem in tail:
                            part += elem.tokens()
                        result = [*result, 'PARTITION BY', *part]
                match ord:
                    case None:
                        pass
                    case list(_):
                        ord_result = []
                        for expr, order_by_spec in ord:
                            curr = expr.tokens()
                            if order_by_spec is not None:
                                curr = [*curr, *order_by_spec.tokens()]
                            ord_result = [*ord_result, *curr]
                        result = [*result, 'ORDER BY', *ord_result]
                match spec:
                    case None:
                        pass
                    case WindowFrameExpression(_):
                        result = [*result, *spec.tokens()]
        return result
    
    def sub_expressions(self) -> List[Expression]:
        exprs = []
        if self.partition_by is not None:
            exprs.append(self.partition_by)
        if self.order_by is not None:
            exprs.append(self.order_by)
        if self.window_frame_clause is not None:
            exprs.append(self.window_frame_clause)
        return [exprs]
    

@dataclass
class AnalyticFunctionExpression(SelectableExpression):
    expr: SelectableExpression
    window_spec_expr: WindowSpecExpression
    
    def tokens(self) -> List[str]:
        return [*self.expr.tokens(), 'OVER', '(', *self.window_spec_expr.tokens(), ')']
    
    def __hash__(self) -> int:
        head, *tail = self.tokens()
        head = head[0]
        for token in tail:
            head += token
        _str = self.__class__.__name__ + head
        return hash(_str)
    
    def sub_expressions(self) -> List[Expression]:
        return [self.expr, self.window_spec_expr]
    
    
    # Functions
class AbstractFunctionExpression(SelectableExpression):
    """abstract method to hold all function expressions

    functions, as expressions, are just a symbol and a list of named arguments
    all functions are created dynamically and are stored within SQLFunctions

    the naming convention is to use the 'symbol' method as the name for the function
    arguments of the functions are not checked for types/expression, but they are checked for their number
    """
    
    @abstractmethod
    def arg_num(self) -> int | List[int | None]:
        pass
    
    @abstractmethod
    def is_legit_number_of_args(self, n: int) -> bool:
        pass

    @abstractmethod
    def symbol(self) -> str:
        pass

    @abstractmethod
    def is_distinct(self) -> bool:
        pass

    def __init__(self, *exprs: SelectableExpression):
        self.exprs = []
        exprs = list(exprs)
        n = len(exprs)
        if not self.is_legit_number_of_args(n):
            raise SyntaxError(f"function {self.symbol} expects a signature with {self.arg_num()} arguments (see __doc__ for FunctionParams), got {n}")
        for arg in list(exprs):
            if not isinstance(arg, SelectableExpression):
                raise TypeError(f"functions expect SelectableExpression, got: {type(arg)}")
            else:
                self.exprs.append(arg)
    
    def tokens(self) -> List[str]:
        result = []
        for expr in self.exprs:
            tkns = expr.tokens()
            if len(result) == 0:
                result = tkns
            else:
                result = [*result, ',', *tkns]
        if self.is_distinct():
            return [f"{self.symbol()}(","DISTINCT", *result, ")"]
        else:
            return [f"{self.symbol()}(", *result, ")"]
        
    def sub_expressions(self) -> List[Expression]:
        return self.exprs
    

class AbstractAggregateFunctionExpression(AbstractFunctionExpression):
    """a sub class to indicate agg funcs"""
    
@dataclass
class FunctionParams:
    """
    A data structure to hold the definitions for a SQL function
    Since there are many SQL functions, and since we still want to adhere to the Expression paradigm, 
    most SQL functions are created dynamically as part of the sql.functions object.
    importing sql, should also import all the methods along with it

    Logic:
        Each SQL function has a unique name (symbol), and an expected number of arguments
        There's no type/expression checking at the moment, the dynamic function will only check if the numebr of arguments inserted is correct
        Some function (see comments below) have specialized sytanx, they will be inserted in a different fashion
        
    Arguments:
        symbol: str - the name of the function, will be converted to upper case
        arg_num: Optional[int | List[int | None]] - 
            if int: minimal number of arguments, None means any number can be inserted
            if list of ints: all posible numbers of inputs
            None: means any number can be inserted
            if a list with an integer and a None - the number is the minimal number of arguments, but can insert any number beyoned the min
        is aggregate: bool - is it an agg function?
        is supporting distinct - does it support distinct? distinct functions must be aggregate functions"""
    symbol: str
    arg_num: Optional[int | List[int | None]]
    is_aggregate: bool=False
    supports_distinct: bool=False

    @classmethod
    def clazz_prefix(cls) -> str:
        return "DynamicFunctionExpression"

    def __post_init__(self):
        self.symbol = ValidName(self.symbol).name
        match self.arg_num:
            case None:
                pass
            case int(_):
                if self.arg_num < 0:
                    raise TypeError("can't have int smaller than 0")
            case list(_):
                count_nones = 0
                for n in self.arg_num:
                    if n is None:
                        count_nones += 1
                    elif isinstance(n, int):
                        if n < 0:
                            raise TypeError()
                    else:
                        raise TypeError("arg_num can be int or None")
                if count_nones == 0:
                    pass
                elif count_nones == 1:
                    if len(self.arg_num) != 2:
                        raise TypeError("when passing [None, ...] to arg_num, there can be only 1 more int")
                else:
                    raise TypeError("can't have more than 1 None in arg_num")
                
    def is_legit_number_of_args(self, n: int) -> bool:
        assert isinstance(n, int)
        assert n >= 0
        match self.arg_num:
            case None:
                return True
            case int(_):
                return self.arg_num == n
            case list(_):
                if None in self.arg_num:
                    # extract the other element that is not None
                    min_, = [x for x in self.arg_num if x is not None]
                    return n >= min_
                else:
                    return n in self.arg_num
                
    def clazz_name(self, is_distinct: bool) -> str:
        suffix = "_DISTINCT" if is_distinct else ""
        return f"{self.clazz_prefix()}{self.symbol.upper()}{suffix}"
                
    def to_expression(self, is_distinct: bool) -> AbstractFunctionExpression:  
        name = self.clazz_name(is_distinct)
        attr = {
                    'arg_num': lambda _: self.arg_num,
                    'symbol': lambda _: self.symbol, 
                    'is_legit_number_of_args': self.is_legit_number_of_args,
                    'is_distinct': lambda _: is_distinct
                }
        
        if self.is_aggregate:
            return type(name, (AbstractAggregateFunctionExpression, ), attr)
        else:    
            return type(name, (AbstractFunctionExpression, ), attr)

                    

class SQLFunctionsGenerator:

    @classmethod
    def _params(cls) -> List[FunctionParams]:
        
        return [
            
            # agg
            FunctionParams("ANY_VALUE", 1, is_aggregate=True, supports_distinct=True),
            FunctionParams("AVG", 1, is_aggregate=True, supports_distinct=True),
            FunctionParams("COUNT", 1, is_aggregate=True, supports_distinct=True),
            FunctionParams("COUNTIF", 1, is_aggregate=True, supports_distinct=True),
            FunctionParams("MAX", 1, is_aggregate=True, supports_distinct=True),
            FunctionParams("MIN", 1, is_aggregate=True, supports_distinct=True),
            FunctionParams("SUM", 1, is_aggregate=True, supports_distinct=True),

            # conditional
            FunctionParams("IFNULL", 2),
            FunctionParams("IF", 3),
            FunctionParams("NULLIF", 2),
            
            # approx
            FunctionParams("APPROX_COUNT_DISTINCT", 1, is_aggregate=True),
            FunctionParams("APPROX_QUANTILES", 2, is_aggregate=True, supports_distinct=True),
            FunctionParams("APPROX_TOP_COUNT", 2, is_aggregate=True),
            FunctionParams("APPROX_TOP_SUM", 3, is_aggregate=True),

            # array
            FunctionParams("ARRAY_CONCAT", None),
            FunctionParams("ARRAY_LENGTH", 1),
            FunctionParams("ARRAY_REVERSE", 1),
            FunctionParams("ARRAY_TO_STRING", [2,3]),
            FunctionParams("GENERATE_ARRAY", [2,3]),
            FunctionParams("GENERATE_DATE_ARRAY", [2,3]),
            FunctionParams("GENERATE_TIMESTAMP_ARRAY", [2,3]),

            # bit
            FunctionParams("BIT_COUNT", 1),
            
            # conversions
            FunctionParams("PARSE_BIGNUMERIC", 1),
            FunctionParams("PARSE_NUMERIC", 1),
            FunctionParams("COALESCE", None),

            # date
            FunctionParams("CURRENT_DATE", 0),
            FunctionParams("DATE", [1,2,3]),
            FunctionParams("DATE_ADD", 2),
            FunctionParams("DATE_FROM_UNIX_DATE", 1),
            FunctionParams("DATE_SUB", 2),
            FunctionParams("DATE_DIFF", 3),
            FunctionParams("DATE_TRUNC", 2),
            FunctionParams("FORMAT_DATE", 2),
            FunctionParams("LAST_DAY", [1,2]),
            FunctionParams("PARSE_DATE", 2),
            FunctionParams("UNIX_DATE", 1),

            # datetime
            FunctionParams("CURRENT_DATETIME", 0),
            FunctionParams("DATETIME", [6,1,2]),
            FunctionParams("DATETIME_ADD", 2),
            FunctionParams("DATETIME_SUB", 2),
            FunctionParams("DATETIME_DIFF", 3),
            FunctionParams("DATETIME_TRUNC", 2),
            FunctionParams("FORMAT_DATETIME", 2),
            FunctionParams("PARSE_DATETIME", 2),

            # debugging
            FunctionParams("ERROR", 1), 

            # hash
            FunctionParams("FARM_FINGERPRINT", 1), 
            FunctionParams("MD5", 1), 
            FunctionParams("SHA1", 1), 
            FunctionParams("SHA256", 1), 
            FunctionParams("SHA512", 1), 

            # json - requires special objects

            # math
            FunctionParams("ABS", 1),
            FunctionParams("ACOS", 1),
            FunctionParams("ACOSH", 1),
            FunctionParams("ASIN", 1),
            FunctionParams("ASINH", 1),
            FunctionParams("ATAN", 1),
            FunctionParams("ATAN2", 2),
            FunctionParams("ATANH", 1),
            FunctionParams("CBRT", 1),
            FunctionParams("CEIL", 1),
            FunctionParams("CEILING", 1),
            FunctionParams("COS", 1),
            FunctionParams("COSH", 1),
            FunctionParams("COSINE_DISTANCE", 2),
            FunctionParams("COT", 1),
            FunctionParams("COTH", 1),
            FunctionParams("CSC", 1),
            FunctionParams("CSCH", 1),
            FunctionParams("DIV", 2),
            FunctionParams("EXP", 1),
            FunctionParams("EUCLIDEAN_DISTANCE", 2),
            FunctionParams("FLOOR", 1),
            FunctionParams("GREATEST", [1,None]),
            FunctionParams("IEEE_DIVIDE", 2),
            FunctionParams("IS_INF", 1),
            FunctionParams("IS_NAN", 1),
            FunctionParams("LEAST", [1,None]),
            FunctionParams("LN", 1),
            FunctionParams("LOG", [1,2]),
            FunctionParams("LOG10", 1),
            FunctionParams("MOD", 2),
            FunctionParams("POW", 2),
            FunctionParams("POWER", 2),
            FunctionParams("RAND", 0),
            FunctionParams("RANGE_BUCKET", 2),
            FunctionParams("ROUND", [1,2,3]),
            FunctionParams("SAFE_ADD", 2),
            FunctionParams("SAFE_DIVIDE", 2),
            FunctionParams("SAFE_MULTIPLY", 2),
            FunctionParams("SAFE_NEGATE", 1),
            FunctionParams("SAFE_SUBTRACT", 2),
            FunctionParams("SEC", 1),
            FunctionParams("SECH", 1),
            FunctionParams("SIGN", 1),
            FunctionParams("SIN", 1),
            FunctionParams("SINH", 1),
            FunctionParams("SQRT", 1),
            FunctionParams("TAN", 1),
            FunctionParams("TANH", 1),
            FunctionParams("TRUNC", [1,2]),
            
            # navigation
            FunctionParams("FIRST_VALUE", 1), # no support for RESPECT|IGNORE
            FunctionParams("LAG", [1,2]),
            FunctionParams("LAST_VALUE", 1), # no support for RESPECT|IGNORE
            FunctionParams("LEAD", [1,2]),
            FunctionParams("NTH_VALUE", 2), # no support for RESPECT|IGNORE
            FunctionParams("PERCENTILE_CONT", 2), # no support for RESPECT|IGNORE
            FunctionParams("PERCENTILE_DISC", 2), # no support for RESPECT|IGNORE

            # numbering
            FunctionParams("CUME_DIST", 0),
            FunctionParams("DENSE_RANK", 0),
            FunctionParams("NTILE", 1),
            FunctionParams("PERCENT_RANK", 0),
            FunctionParams("RANK", 0),
            FunctionParams("ROW_NUMBER", 0),
        

            # range
            FunctionParams("GENERATE_RANGE_ARRAY", [2,3]),
            FunctionParams("RANGE", 2),
            FunctionParams("RANGE_CONTAINS", 2),
            FunctionParams("RANGE_END", 1),
            FunctionParams("RANGE_INTERSECT", 2),
            FunctionParams("RANGE_OVERLAPS", 2),
            FunctionParams("RANGE_SESSIONIZE", [3,4]),
            FunctionParams("RANGE_START", 1),
            
            # security
            FunctionParams("SESSION_USER", 0),

            # stat aggregates
            FunctionParams("CORR", 2, is_aggregate=True),
            FunctionParams("COVAR_POP", 2, is_aggregate=True),
            FunctionParams("COVAR_SAMP", 2, is_aggregate=True),
            FunctionParams("STDDEV", 1, is_aggregate=True, supports_distinct=True),
            FunctionParams("STDDEV_POP", 1, is_aggregate=True, supports_distinct=True),
            FunctionParams("STDDEV_SAMP", 1, is_aggregate=True, supports_distinct=True),
            FunctionParams("VAR_POP", 1, is_aggregate=True, supports_distinct=True),
            FunctionParams("VAR_SAMP", 1, is_aggregate=True, supports_distinct=True),
            FunctionParams("VARIANCE", 1, is_aggregate=True, supports_distinct=True),

            # string
            FunctionParams("ASCII", 1),
            FunctionParams("BYTE_LENGTH", 1),
            FunctionParams("CHAR_LENGTH", 1),
            FunctionParams("CHARACTER_LENGTH", 1),
            FunctionParams("CHR", 1),
            FunctionParams("CODE_POINTS_TO_BYTES", 1),
            FunctionParams("CODE_POINTS_TO_STRING", 1),
            FunctionParams("COLLATE", 2),
            FunctionParams("CONCAT", None),
            FunctionParams("CONTAINS_SUBSTR", 2), # no support for json scope
            FunctionParams("EDIT_DISTANCE", 2), # no support for max
            FunctionParams("ENDS_WITH", 2), 
            FunctionParams("FORMAT", 2), # no support for format specifiers
            FunctionParams("FROM_BASE32", 1), 
            FunctionParams("FROM_BASE64", 1), 
            FunctionParams("INITCAP", [1,2]), 
            FunctionParams("INSTR", [2,3,4]), 
            FunctionParams("LEFT", 2), 
            FunctionParams("LENGTH", 1), 
            FunctionParams("LOWER", 1), 
            FunctionParams("LPAD", [2,3]), 
            FunctionParams("LTRIM", [1,2]), 
            FunctionParams("NORMALIZE", [1,2]), 
            FunctionParams("NORMALIZE_AND_CASEFOLD", [1,2]), 
            FunctionParams("OCTET_LENGTH", 1), 
            FunctionParams("REGEXP_CONTAINS", [1,2]), 
            FunctionParams("REGEXP_EXTRACT", [2,3,4]), 
            FunctionParams("REGEXP_EXTRACT_ALL", 2), 
            FunctionParams("REGEXP_INSTR", [2,3,4,5]), 
            FunctionParams("REGEXP_REPLACE", 3), 
            FunctionParams("REGEXP_SUBSTR", [2,3,4]), 
            FunctionParams("REPEAT", 2), 
            FunctionParams("REPLACE", 3), 
            FunctionParams("REVERSE", 1), 
            FunctionParams("RIGHT", 2), 
            FunctionParams("RPAD", [2,3]), 
            FunctionParams("RTRIM", [1,2]), 
            FunctionParams("SAFE_CONVERT_BYTES_TO_STRING", 1), 
            FunctionParams("SOUNDEX", 1), 
            FunctionParams("SPLIT", [1,2]), 
            FunctionParams("STARTS_WITH", 2), 
            FunctionParams("STRPOS", 2), 
            FunctionParams("SUBSTR", [2,3]), 
            FunctionParams("SUBSTRING", [2,3]), 
            FunctionParams("TO_BASE32", 1), 
            FunctionParams("TO_BASE64", 1), 
            FunctionParams("TO_CODE_POINTS", 1), 
            FunctionParams("TO_HEX", 1), 
            FunctionParams("TRANSLATE", 3), 
            FunctionParams("TRIM", [1,2]), 
            FunctionParams("UNICODE", 1), 
            FunctionParams("UPPER", 1), 
            
            # text analysis
            FunctionParams("BAG_OF_WORDS", 1), 
            FunctionParams("TF_IDF", [1,2,3]), 

            # time
            FunctionParams("CURRENT_TIME", [0,1]), 
            FunctionParams("FORMAT_TIME", 2), 
            FunctionParams("PARSE_TIME", 2), 
            FunctionParams("TIME", [1,2,3]), 
            FunctionParams("TIME_ADD", 2), 
            FunctionParams("TIME_DIFF", 3), 
            FunctionParams("TIME_SUB", 2), 
            FunctionParams("TIME_TRUNC", 2), 
            
            # time series
            FunctionParams("DATE_BUCKET", [2,3]), 
            FunctionParams("DATETIME_BUCKET", [2,3]), 
            FunctionParams("TIMESTAMP_BUCKET", [2,3]), 

            # timestamp
            FunctionParams("CURRENT_TIMESTAMP", 0),
            FunctionParams("FORMAT_TIMESTAMP", [2,3]), 
            FunctionParams("PARSE_TIMESTAMP", [2,3]), 
            FunctionParams("TIMESTAMP", [1,2]), 
            FunctionParams("TIMESTAMP_ADD", 2), 
            FunctionParams("TIMESTAMP_DIFF", 3), 
            FunctionParams("TIMESTAMP_MICROS", 1), 
            FunctionParams("TIMESTAMP_MILLIS", 1), 
            FunctionParams("TIMESTAMP_SECONDS", 1), 
            FunctionParams("TIMESTAMP_SUB", 2), 
            FunctionParams("TIMESTAMP_TRUNC", [2,3]), 
            FunctionParams("UNIX_MICROS", 1), 
            FunctionParams("UNIX_MILLIS", 1), 
            FunctionParams("UNIX_SECONDS", 1), 
            
            # utility
            FunctionParams("GENERATE_UUID", 0),
            
        ]
    
    def __init__(self, *args: FunctionParams) -> None:
        args = list(args)
        if len(args) == 0:
            args = self._params()
        for param in args:
            setattr(self, param.clazz_name(False), param.to_expression(False))
            if param.supports_distinct:
                setattr(self, param.clazz_name(True), param.to_expression(True))
                
@dataclass
class CaseExpression(SelectableExpression):
    cases: List[Tuple[SelectableExpression, SelectableExpression]]
    otherwise: Optional[SelectableExpression]=None

    def __post_init__(self):
        for cond, value in self.cases:
            if not isinstance(cond, SelectableExpression) or not isinstance(value, SelectableExpression):
                raise TypeError()
        if self.otherwise is not None:
            if not isinstance(self.otherwise, SelectableExpression):
                if isinstance(self.otherwise, int | float | str | bool):
                    self.otherwise = LiteralExpression(self.otherwise)
                else:
                    raise TypeError(f"unsupported type for otherwise, got {type(self.otherwise)=}")

    def add(self, condition: SelectableExpression, value: SelectableExpression) -> CaseExpression:
        new_cases = [*self.cases, (condition, value)]
        return CaseExpression(new_cases, self.otherwise)

    def add_otherwise(self, otherwise: SelectableExpression) -> CaseExpression:
        return CaseExpression(self.cases, otherwise)

    @classmethod
    def _case_to_sql(cls, operation: SelectableExpression, expr: SelectableExpression) -> List[str]:
        return ['WHEN', *operation.tokens(), 'THEN', *expr.tokens()]
    
    def case_tokens(self) -> List[str]:
        cases = []
        for operation, expr in self.cases:
            cases += self._case_to_sql(operation, expr)
        otherwise = [] if self.otherwise is None else ['ELSE', *self.otherwise.tokens()]
        return cases + otherwise
    
    def tokens(self) -> List[str]:
        if len(self.cases) == 0:
            raise ValueError("can't render to sql with 0 cases")
        return ['CASE', *self.case_tokens(), 'END']
    
    def sub_expressions(self) -> List[Expression]:
        exprs = []
        for cond, value in self.cases:
            exprs.append(cond)
            exprs.append(value)
        if self.otherwise is not None:
            exprs.append(self.otherwise)
        return exprs
    

class ExistsOperatorExpression(SelectableExpression):

    def __init__(self, query: QueryableExpression):
        if not isinstance(query, QueryableExpression):
            raise TypeError()
        self.query = query

    def tokens(self) -> List[str]:
        return ['EXISTS', '(', *self.query.tokens(), ')']
    
    def sub_expressions(self) -> List[Expression]:
        return [self.query]

