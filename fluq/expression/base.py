
from __future__ import annotations

from fluq.render import Renderable

from typing import List, Tuple, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
import string
import re


# Naming of objects
@dataclass
class ValidName:
    """asserts that a name str is a proper valid name for columns/tables/aliases
    
    Usage:
        >>> valid_name: ValidName = ValidName('foo')
        >>> print(valid_name.name) # Output: foo

        >>> ValidName('23my_col') # Raises: TypeError

        can also be used with `backticks`:
        >>> print(ValidName('`foo bar`').name) # Output: `foo bar`
    
    Raises:
        TypeError for invalide names
    """
    _name: str
    _backticks: bool=False
    
    @property
    def allowed_first_chars(self) -> str:
        return ''.join(['_', *string.ascii_letters])
    
    @property
    def allowed_last_chars(self) -> str:
        return self.allowed_first_chars + string.digits
    
    def allowed_mid_chars(self, is_project_name: bool=False) -> str:
        return self.allowed_last_chars + "." + ("-" if is_project_name else '')
    
    @staticmethod
    def remove_redundant_dots(s: str):
        return re.sub(r'\.+', '.', s)

    def check_bad_chars(self, 
                        partial_name: str, 
                        bad_chars: List[Tuple[int, str]], 
                        is_project_name: bool, 
                        offset: int=0) -> List[Tuple[int, str]]:
        for i, char in enumerate(partial_name):
            bad_char_condition = (i == 0 and char not in self.allowed_first_chars)
            bad_char_condition |= (0 < i < len(partial_name)-1 and char not in self.allowed_mid_chars(is_project_name))
            bad_char_condition |= (i == len(partial_name)-1 and char not in self.allowed_last_chars)
            if bad_char_condition:
                bad_chars.append((i + offset, char))
        return bad_chars


    def __post_init__(self):
        bad_chars: List[Tuple[int, str]] = []
        match (self._name, len(self._name)):
            case (ValidName(name), _):
                self._name = name
            case (_, 0):
                raise SyntaxError("name cannot be an empty str")
            case (str(char), 1):
                if char in self.allowed_first_chars:
                    self._name = char
                else:
                    raise SyntaxError(f"'{char}' is not a valid single character name")
            case (str(name), _) if name[0] == '`' and name[-1] == '`':
                self._name = name[1:-1]
                self._backticks = True
            case (str(name), _) if len(name.split('.')) > 3:
                raise SyntaxError(f"db paths can be triple at most, got {len(name.split('.'))}")
            case (str(name), _) if len(name.split('.')) == 3:
                offset = 0
                result = ''
                for i, spl in enumerate(name.split(',')):
                    bad_chars = self.check_bad_chars(spl, 
                                                     bad_chars=bad_chars, 
                                                     is_project_name=True if i==0 else False, 
                                                     offset=offset)
                    if result == '':
                        result = spl
                    else:
                        result += f".{spl}"
                    offset += 1+len(spl)
                self._name = result
            case (str(name), _) if len(name.split('.')) == 2:
                offset = 0
                result = ''
                for i, spl in enumerate(name.split(',')):
                    bad_chars = self.check_bad_chars(spl, 
                                                     bad_chars=bad_chars, 
                                                     is_project_name=False, 
                                                     offset=offset)
                    if result == '':
                        result = spl
                    else:
                        result += f".{spl}"
                    offset += 1+len(spl)
                self._name = result
            case (str(name), _) if len(name.split('.')) == 1:
                bad_chars = self.check_bad_chars(name, bad_chars=bad_chars, is_project_name=False, offset=0)
                self._name = name
        if len(bad_chars) > 0:
            raise TypeError(f"illegal name, due to bad characters in these locations: {bad_chars}")
        self._name = self.remove_redundant_dots(self._name)

    def last_identifer(self) -> str:
        return self._name.split('.')[-1]
    
    @property
    def name(self) -> str:
        if self._backticks:
            return f"`{self._name}`"
        else:
            return self._name


# Expressions
class Expression(ABC):
    """This is the basic workhorse to hold a query and understand it
    
    Methods:

        sql (property) - the Renderable object that holds the SQL str

        __hash__ - for storing in dicts, sets and for comparing to other expressions
        __eq__ - only between other expressions
        
        tokens (abstract) - each expression should be able to return tokens that mak up the SQL str 
            the expression is supposed to represent. it is up to the implementer to decide how to break it down
        
        sub_expressions (abstract) - a list of all sub-expressions (not recursive)
        filter - a method to recursively go through all sub expressions and filter them by a predicate

    """

    @property
    def sql(self) -> Renderable:
        """The SQL str (Renedrable object that behaves like a str) of the expression"""
        return Renderable(tokens=self.tokens())
        
    def __hash__(self) -> int:
        return hash(self.__class__.__name__ + ''.join(self.tokens()))
    
    def __eq__(self, __value: object) -> bool:
        match __value:
            case Expression():
                return hash(self) == hash(__value)
            case _:
                return False
    
    @abstractmethod
    def tokens(self) -> List[str]:
        """A list of all str tokens that make up the SQL str according to their display order"""
        pass

    @abstractmethod
    def sub_expressions(self) -> List[Expression]:
        """all 1 level subexpressions, not recursive."""
        pass
    
    def filter(self, predicate: Callable[[Expression], bool]) -> List[Expression]:
        """return all sub-expressions (recursive) that meet a predicate
        
        Usage:
            >>> from fluq.sql import *
            >>> from fluq.frame import Frame
            >>>
            >>> query: Frame = select(col("a"), col("b"), col("c"))
            >>> filtered = query._get_expr().filter(lambda e: e.tokens()[0] == "a")[0]_name.name
            >>> print(filtered) # Output: a
        """
        result = []
        for expr in self.sub_expressions():
            if predicate(expr):
                result.append(expr)
            result = [*result, *expr.filter(predicate)]
        return result



class TerminalExpression(Expression):
    """an expression that has no sub_expressions"""

    def sub_expressions(self) -> List[Expression]:
        return []


class SelectableExpression(Expression):
    """a base class for everything one can put in SELECT, WHERE, GROUP BY .... clauses"""
    pass 

class JoinableExpression(Expression):
    """anything that can be joined"""
    pass

class QueryableExpression(JoinableExpression):
    """abstract flag for queries of all types"""
    pass

@dataclass
class TableNameExpression(JoinableExpression, TerminalExpression):
    db_path: ValidName

    def __post_init__(self):
        assert isinstance(self.db_path, ValidName | str), f"only supported ValidName | str, got {type(self.db_path)=}"
        if isinstance(self.db_path, str):
            self.db_path = ValidName(self.db_path)

    def tokens(self) -> List[str]:
        return [self.db_path.name]

    
class ResultSet(ABC):
    """a basic class to serve Frame and other Frame like classes - basically to help prevent circular imports"""

    def _get_expr(self) -> Expression:
        pass