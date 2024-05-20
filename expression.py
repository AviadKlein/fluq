
from __future__ import annotations

from typing import Any, List, Tuple, Optional, Dict
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
import string
import re


# Naming of objects
@dataclass
class ValidName:
    """asserts that a name str is a proper valid name for columns"""
    name: str
    
    @property
    def allowed_first_chars(self) -> str:
        return ''.join(['_', *string.ascii_letters])
    
    @property
    def allowed_last_chars(self) -> str:
        return self.allowed_first_chars + string.digits
    
    @property
    def allowed_mid_chars(self) -> str:
        return self.allowed_last_chars + "."
    
    @staticmethod
    def remove_redundant_dots(s: str):
        return re.sub(r'\.+', '.', s)

    def __post_init__(self):
        match self.name:
            case ValidName(name):
                self.name = name
            case str(name) if len(name) == 0:
                raise TypeError("name cannot be an empty str")
            case str(name) if name[0] == '`' and name[-1] == '`':
                self.name = name
            case str(name): 
                bad_chars: List[Tuple[int, str]] = []
                for i, char in enumerate(self.name):
                    bad_char_condition = (i == 0 and char not in self.allowed_first_chars)
                    bad_char_condition |= (0 < i < len(name)-1 and char not in self.allowed_mid_chars)
                    bad_char_condition |= (i == len(name)-1 and char not in self.allowed_last_chars)
                    if bad_char_condition:
                            bad_chars.append((i, char))
                if len(bad_chars) > 0:
                    raise TypeError(f"illegal name, due to bad characters in these locations: {bad_chars}")
        self.name = self.remove_redundant_dots(self.name)


# Indentation and formatting
@dataclass
class Indent:
    """class to hold instructions for indentation"""
    indents: int = 0
    indent_str: str = '\t'

    def render(self) -> str:
        return f"{self.indent_str*self.indents}"
    
    def __str__(self) -> str:
        return self.render()
    
    def plus1(self) -> Indent:
        return Indent(self.indents+1, self.indent_str)


# TODO - refactor expressions as dataclass wherever possible
# TODO - add a depth int to all expressions for more sophisticated rendering 
    # Rendering should be controlled by a Style object, that has a default.

# Expressions
class Expression(ABC):
    """This is the basic workhorse
    expressions 'sql' themselves and can hold other expressions"""

    @abstractmethod
    def unindented_sql(self) -> str:
        pass

    @property
    def sql(self, indent: Indent = Indent()) -> str:
        return f"{indent}{self.unindented_sql()}"
    
    def __eq__(self, __value: object) -> bool:
        cond = (self.__class__.__name__ == __value.__class__.__name__)
        cond &= isinstance(__value, Expression)
        cond &= self.unindented_sql() == __value.unindented_sql()
        if cond:
            return True
        else:
            return False
        
    def __hash__(self) -> int:
        return hash(self.__class__.__name__ + self.unindented_sql())
    

class AnyExpression(Expression):
    """just in case you need to solve something"""

    def __init__(self, expr: str):
        self.expr = expr

    def unindented_sql(self) -> str:
        return self.expr
    
    

class TableNameExpression(Expression):

    def __init__(self, db_path: ValidName | str):
        assert isinstance(db_path, ValidName | str), f"only supported ValidName | str, got {type(db_path)=}"
        if isinstance(db_path, str):
            db_path = ValidName(db_path)
        self.db_path = db_path

    def unindented_sql(self) -> str:
        return self.db_path.name



class ToLogicalMixin(Expression):
    """a mixin to turn a logical or math or just a pointer or literal into a logical expression"""

    def to_logical(self) -> LogicalOperationExpression:
        return IsNotNull(self)


class ColumnExpression(ToLogicalMixin):
    """when you just want to point to a column"""

    def __init__(self, name: str):
        if name == "*":
            self._name = "*"
        else:
            self._name = ValidName(name)

    @property
    def name(self) -> str:
        return "*" if self._name == "*" else self._name.name
    
    def unindented_sql(self) -> str:
        return self.name


LiteralTypes = int | float | bool | str

class LiteralExpression(ToLogicalMixin):
    """to hold numbers, strings, booleans"""
    
    def __init__(self, value: LiteralTypes) -> None:
        super().__init__()
        self.value = value
        if isinstance(value, bool):
            self.sql_value = str(value).upper()
        elif isinstance(value, str):
            self.sql_value = f"'{value}'"
        elif isinstance(value, (float, int)):
            self.sql_value = str(value)
        else:
            raise TypeError()


    def unindented_sql(self) -> str:
        return self.sql_value
    
class NegatedExpression(ToLogicalMixin):
    """negate an expression"""

    def __init__(self, expr: Expression) -> None:
        assert isinstance(expr, Expression)
        self.expr = expr

    def unindented_sql(self) -> str:
        return f"-{self.expr.unindented_sql()}"


class NullExpression(ToLogicalMixin):
    """a special expression for the NULL value"""

    def unindented_sql(self) -> str:
        return "NULL"


class AbstractOperationExpression(ToLogicalMixin):
    """an expression to denote an operation between 2 expressions
    this is supposed to serve:
    a + 2
    3 * 9
    a is NULL
    a is in ()

    etc.
    """
    
    def __init__(self, left: Expression, right: Expression):
        assert isinstance(left, Expression)
        assert isinstance(right, Expression)
        self.left = left
        self.right = right
    
    @property
    def _wrap_left(self) -> bool:
        """should wrap the left hand side with parenthesis"""
        return False
    
    @property
    def _wrap_right(self) -> bool:
        """should wrap the left hand side with parenthesis"""
        return False
    
    @abstractmethod
    def op_str(self) -> str:
        """the string that will be presented in the SQL str"""
        pass

    def unindented_sql(self) -> str:
        """the SQL str"""
        _left = self.left.unindented_sql()
        if self._wrap_left:
            _left = f"({_left})"
        
        _right = self.right.unindented_sql()
        if self._wrap_right:
            _right = f"({_right})"
        return f"{_left} {self.op_str} {_right}"


class LogicalOperationExpression(AbstractOperationExpression):
    """just a flag to differentiate between logical ops to math ops"""
    pass

class MathOperationExpression(AbstractOperationExpression):
    """just a flag to differentiate between logical ops to math ops"""
    pass


class Equal(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return "="
    

class NotEqual(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return "<>"
    

class Greater(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return ">"
    

class GreaterOrEqual(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return ">="
    

class Less(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return "<"
    

class LessOrEqual(LogicalOperationExpression):

    @property
    def op_str(self) -> str:
        return "<="
    

class In(LogicalOperationExpression):

    def __init__(self, left: Expression, 
                 *args: Expression | LiteralTypes | QueryExpression):
        assert isinstance(left, Expression)
        self.left = left
        self.is_query = False

        # assert only 1 QueryExpression
        _num_queries = sum([1 for _ in args if isinstance(_, QueryExpression)])
        assert _num_queries <= 1

        if _num_queries == 1:
            assert len(args) == 1
            self.is_query = True
            self.query = args[0]
        elif all([isinstance(_, Expression) for _ in args]):
            self._list = args
        elif all([isinstance(_, (int, float)) for _ in args]) or \
            all([isinstance(_, bool) for _ in args]) or \
            all([isinstance(_, str) for _ in args]):
            self._list = [LiteralExpression(_) for _ in args]
        else:
            msg = "list of expressions can be Expression | LiteralTypes | FutureExpression"
            msg += "\n"
            msg += f"{args} has types: ({[type(_) for _ in args]}), respectively"
            raise TypeError(msg)

    @property
    def op_str(self) -> str:
        return "IN"

    def unindented_sql(self) -> str:
        if self.is_query:
            return f"{self.left.unindented_sql()} {self.op_str} ( {self.query.sql} )"
        else:
            resolved_str = ', '.join([_.sql for _ in self._list])
            return f"{self.left.unindented_sql()} {self.op_str} ({resolved_str})"
    
class Not(NotEqual):

    def __init__(self, expr: Expression):
        super().__init__(left=expr, right=LiteralExpression(True))

class IsNull(Equal):

    def __init__(self, expr: Expression):
        super().__init__(left=expr, right=NullExpression())

    @property
    def op_str(self) -> str:
        return "IS"
    

class IsNotNull(NotEqual):

    def __init__(self, expr: Expression):
        super().__init__(left=expr, right=NullExpression())

    @property
    def op_str(self) -> str:
        return "IS NOT"
    
class Between(LogicalOperationExpression):

    def __init__(self, left: Expression, from_: Expression, to: Expression):
        assert isinstance(left, Expression)
        assert isinstance(from_, Expression)
        assert isinstance(to, Expression)
        self.left = left
        self.from_ = from_
        self.to = to

    @property
    def op_str(self) -> str:
        return "BETWEEN"
    
    def unindented_sql(self) -> str:
        return f"{self.left.unindented_sql()} {self.op_str} {self.from_.unindented_sql()} AND {self.to.unindented_sql()}"
    
class And(LogicalOperationExpression):

    @property
    def _wrap_left(self) -> bool:
        return True
    
    @property
    def _wrap_right(self) -> bool:
        return True
    
    @property
    def op_str(self) -> str:
        return "AND"
    

class Or(LogicalOperationExpression):

    @property
    def _wrap_left(self) -> bool:
        return True
    
    @property
    def _wrap_right(self) -> bool:
        return True
    
    @property
    def op_str(self) -> str:
        return "OR"
    
class Like(LogicalOperationExpression):
    
    @property
    def op_str(self) -> str:
        return "LIKE"
    

class Plus(MathOperationExpression):

    @property
    def op_str(self) -> str:
        return "+"
    

class Minus(MathOperationExpression):

    @property
    def op_str(self) -> str:
        return "-"
    

class Multiply(MathOperationExpression):

    @property
    def op_str(self) -> str:
        return "*"
    

class Divide(MathOperationExpression):

    @property
    def op_str(self) -> str:
        return "/"
    

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


@dataclass
class AnalyticFunctionExpression(Expression):
    expr: SelectableExpressionType
    window_spec_expr: WindowSpecExpression

    def unindented_sql(self) -> str:
        return f"{self.expr.unindented_sql()} OVER({self.window_spec_expr.unindented_sql()})"


class JoinOperationExpression(Expression):
    """a base class for all relational operations"""

    def __init__(self,
                 left: TableNameExpression | QueryExpression | JoinOperationExpression,
                 right: TableNameExpression | QueryExpression,
                 left_alias: Optional[str]=None,
                 right_alias: Optional[str]=None,
                 on: Optional[LogicalOperationExpression]=None):
        assert isinstance(left, TableNameExpression | QueryExpression | JoinOperationExpression)
        assert isinstance(right, TableNameExpression | QueryExpression)
        if on is not None:
            assert isinstance(on, LogicalOperationExpression)

        self.left = left
        self.right = right
        
        self.left_alias = ValidName(left_alias).name if left_alias is not None else None
        self.right_alias = ValidName(right_alias).name if right_alias is not None else None

        if isinstance(self.left, JoinOperationExpression):
            assert self.left_alias is None, f"JoinOperationExpression can't have an alias"
        if isinstance(self.left, QueryExpression):
            assert self.left_alias is not None, "left QueryExpression must have an alias"
        if isinstance(self.right, QueryExpression):
            assert self.right_alias is not None, "right QueryExpression must have an alias"

        
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
        elif isinstance(side, QueryExpression):
            return f"({side.sql}) AS {alias}"
        else:
            raise TypeError()       

    def unindented_sql(self) -> str:
        left = self.resolve_sql("left")
        right = self.resolve_sql("right")
        return f"{left} {self.operator()} {right}{self.on_clause()}"


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
    
       

# Clauses
class ClauseExpression(Expression):
    """abstract for clauses (i.e. Select, From, Where, ...)"""
    

# Select
SelectableExpressionType = LiteralExpression | ColumnExpression | \
    LogicalOperationExpression | MathOperationExpression | NullExpression | AbstractFunctionExpression | \
    CaseExpression


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
                        assert isinstance(query, QueryAble)
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
        if isinstance(self.from_item, QueryAble):
            from_item_str = f"({from_item_str})"
        if self.alias is not None:
            from_item_str = f"{from_item_str} AS {self.alias}"
        return f"FROM {from_item_str}"


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

@dataclass
class OrderBySpecExpression(Expression):
    asc: bool=True
    nulls: str="FIRST"
    
    def __post_init__(self):
        assert isinstance(self.asc, bool)
        assert isinstance(self.nulls, str) and self.nulls in ("FIRST", "LAST")

    def unindented_sql(self) -> str:
        result = "ASC" if self.asc else "DESC"
        result += f" NULLS {self.nulls}"
        return result

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
    
class QueryAble(Expression):
    
    @abstractmethod
    def copy(self):
        pass

@dataclass
class QueryExpression(QueryAble):
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
    
    def unindented_sql(self) -> str:
        return '\n'.join([_.unindented_sql() for _ in self.clause_ordering() if _ is not None])
    
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
    

class UnionQueryExpression(QueryAble):

    def __init__(self, a: QueryExpression, b: QueryExpression):
        raise NotImplementedError()
    
# Specs

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
                        
        