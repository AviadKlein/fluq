
from __future__ import annotations

from typing import Any, List, Tuple, Optional
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
        if isinstance(self.name, ValidName):
            pass
        else:
            length = len(self.name)
            assert length > 0, "name cannot be an empty str"
            bad_chars: List[Tuple[int, str]] = []
            
            for i, char in enumerate(self.name):
                bad_char_condition = (i == 0 and char not in self.allowed_first_chars)
                bad_char_condition |= (0 < i < length-1 and char not in self.allowed_mid_chars)
                bad_char_condition |= (i == length-1 and char not in self.allowed_last_chars)
                if bad_char_condition:
                        bad_chars.append((i, char))
            if len(bad_chars) > 0:
                raise Exception(f"illegal name, due to bad characters in these locations: {bad_chars}")
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


# Expressions
class Expression(ABC):
    """This is the basic workhorse"""

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
    

class AnyExpression(Expression):
    """just in case you need to solve something"""

    def __init__(self, expr: str):
        self.expr = expr

    def unindented_sql(self) -> str:
        return self.expr
        
    

class FutureExpression(Expression):
    """this is a place holder for until I solve the issue of subqueries used in the logical:
    col IN (select from ...)"""
    

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
    

class TableNameExpression(Expression):

    def __init__(self, db_path: ValidName | str):
        assert isinstance(db_path, ValidName | str), f"only supported ValidName | str, got {type(db_path)=}"
        if isinstance(db_path, str):
            db_path = ValidName(db_path)
        self.db_path = db_path

    def unindented_sql(self) -> str:
        return self.db_path.name
        


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
                 *args: Expression | LiteralTypes | FutureExpression):
        assert isinstance(left, Expression)
        self.left = left

        # resolve list of expressions
        if isinstance(args, tuple):
            if len(args) == 1 and isinstance(args[0], FutureExpression):
                self._list = args[0]
                raise NotImplementedError("yet to implement FutureExpression")
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
    
class And(AbstractOperationExpression):

    @property
    def _wrap_left(self) -> bool:
        return True
    
    @property
    def _wrap_right(self) -> bool:
        return True
    
    @property
    def op_str(self) -> str:
        return "AND"
    

class Or(AbstractOperationExpression):

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
    def _case_to_sql(cls, operation: Expression, expr: Expression, indent: Indent) -> str:
        return f"{indent}WHEN {operation.unindented_sql()} THEN {expr.unindented_sql()}"
    
    def unindented_sql(self) -> str:
        return self.sql(indent = Indent())
    
    @property
    def sql(self, indent: Indent = Indent()) -> str:
        if len(self.cases) == 0:
            raise ValueError("can't render to sql with 0 cases")
        cases = [self._case_to_sql(operation, expr, indent.plus1()) for operation, expr in self.cases]
        cases = '\n'.join(cases)
        otherwise = "" if self.otherwise is None else f"\n{indent.plus1()}ELSE {self.otherwise.unindented_sql()}"
        return f"{indent}CASE\n{cases}{otherwise}\n{indent}END"
    


class JoinOperationExpression(Expression):
    """a base class for all relational operations"""

    def __init__(self,
                 left: TableNameExpression | JoinOperationExpression,
                 right: TableNameExpression,
                 left_alias: Optional[str]=None,
                 right_alias: Optional[str]=None,
                 on: Optional[LogicalOperationExpression]=None):
        assert isinstance(left, Expression)
        assert isinstance(right, Expression)
        if on is not None:
            assert isinstance(on, LogicalOperationExpression)

        self.left = left
        self.right = right
        
        self.left_alias = ValidName(left_alias).name if left_alias is not None else None
        if isinstance(self.left, JoinOperationExpression):
            assert self.left_alias is None, f"JoinOperationExpression can't have an alias"

        self.right_alias = ValidName(right_alias).name if right_alias is not None else None

        # if both right and left aliases are not None assert they are not the same
        if (self.left_alias is not None) and (self.right_alias is not None):
            assert self.left_alias != self.right_alias
        self.on = on

        duplicates = [item for item, count in Counter(self.aliases()).items() if count > 1]
        if len(duplicates) > 0:
            raise TypeError(f"can't have duplicate aliases for tables, found: {', '.join(duplicates)}")


    
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

    def unindented_sql(self) -> str:
        left = self.left.sql
        if self.left_alias is not None:
            left = f"{left} AS {self.left_alias}"
        right = self.right.sql
        if self.right_alias is not None:
            right = f"{right} AS {self.right_alias}"
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
    """abstract method to hold all functions"""
    pass
        

# Clauses
class ClauseExpression(Expression):
    """abstract for clauses (i.e. Select, From, Where, ...)"""
    

# Select
SelectableExpressionType = LiteralExpression | ColumnExpression | \
    LogicalOperationExpression | MathOperationExpression | NullExpression | AbstractFunctionExpression | \
    CaseExpression


class SelectExpression(ClauseExpression):

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

    def _resolve_arg(self, arg: SelectableExpressionType | Tuple[SelectableExpressionType, Optional[ValidName | str]]) -> Tuple[SelectableExpressionType, Optional[ValidName | str]]:
        if not isinstance(arg, tuple):
            assert isinstance(arg, self.allowed_expression_types())
            if arg == ColumnExpression("*"):
                assert not self._has_star, """can only have 1 ColumnExpression("*")"""
            return arg, None
        elif isinstance(arg, tuple):
            assert len(arg) == 2
            expr, optional_alias = arg
            assert isinstance(expr, self.allowed_expression_types())
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
            

    
    def add(self, expression: SelectableExpressionType, alias: Optional[ValidName | str]=None) -> SelectExpression:
        expr, optional_alias = self._resolve_arg((expression, alias))

        return SelectExpression(
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
            CaseExpression])

    @classmethod
    def from_args(cls, *args: Tuple[SelectableExpressionType, Optional[ValidName]]) -> SelectExpression:
        result = SelectExpression([],[])
        for arg in args:
            if not isinstance(arg, tuple):
                result = result.add(arg, None)
            elif isinstance(arg, tuple):
                assert len(arg) == 2
                result = result.add(arg[0], arg[1])
            else:
                raise TypeError(f"Only Tuple[SelectableExpressionType, Optional[ValidName]] are supported as args, got {type(arg)=}")
        return result


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
    """
    
    def __init__(self, **kwargs) -> None:
        match len(kwargs):
            case 1:
                key = list(kwargs.keys())[0]
                match key:
                    case 'table' | 'join_expression':
                        item = kwargs[key]
                        assert isinstance(item, str | TableNameExpression | JoinOperationExpression)
                        if isinstance(item, str):
                            item = TableNameExpression(item)
                        self.from_item = item
                        self._alias = None
                    case _:
                        raise TypeError(f"when calling with 1 key word argument, \
                                        only 'table' and 'join_expression' are supported, got '{key}'")
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
                        
                    case _:
                        raise TypeError(f"when calling with 2 key word arguments, \
                                        only 'table' and 'alias' are supported, got '{key1}' and '{key2}'")
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
    
    def unindented_sql(self) -> str:
        # resolve item:
        from_item_str = self.from_item.sql
        if self.alias is not None:
            from_item_str = f"{from_item_str} AS {self.alias}"
        return f"FROM {from_item_str}"
        



        
        
            
            
            


        
    
    