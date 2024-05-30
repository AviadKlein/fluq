
from __future__ import annotations

from sparkit.render import Renderable

from typing import List, Tuple
from abc import ABC, abstractmethod
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


# Expressions
class Expression(ABC):
    """This is the basic workhorse
    expressions 'sql' themselves and can hold other expressions"""

    @property
    def sql(self) -> Renderable:
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
        pass

class TableNameExpression(Expression):

    def __init__(self, db_path: ValidName | str):
        assert isinstance(db_path, ValidName | str), f"only supported ValidName | str, got {type(db_path)=}"
        if isinstance(db_path, str):
            db_path = ValidName(db_path)
        self.db_path = db_path

    def tokens(self) -> List[str]:
        return [self.db_path.name]

class SelectableExpression(Expression):
    """a base class for everything one can put in SELECT, WHERE, GROUP BY .... clauses"""
    pass  

class Queryable(Expression):
    """abstract flag for queries of all types"""
    pass

class ResultSet:
    """a basic class to serve Frame and other Frame like classes - basically to help prevent circular imports"""