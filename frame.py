from __future__ import annotations

from typing import Union, Optional, List, Tuple
from collections import OrderedDict
from enum import Enum, auto

from datatype import DataType
from expression import ValidName
from column import Column



Identifier = Union[str, ValidName, Column]
TableIdentifier = Union[str, ValidName]

class JoinTypeEnum(Enum):
    inner = auto()
    left = auto()
    right = auto()
    full = auto()
    cartesian = auto()

class Base:
    pass



    


class Frame:

    def __init__(self, logical_plan):
        pass


    @classmethod
    def from_table_identifier(cls, table_identifier: TableIdentifier) -> Frame:
        pass
    
    @classmethod
    def from_schema(cls, schema: OrderedDict[ValidName, DataType]) -> Frame:
        pass
    
    @classmethod
    def from_db(cls, full_path: str) -> Frame:
        pass

    def select(self, *args: str | List[str] | List[Column]) -> Frame:
        pass

    def where(self, predicate: Column) -> Frame:
        pass
    
    def join(self, other: Frame, join_type: str | JoinTypeEnum, on: Column) -> Frame:
        pass

    def cartesian(self, other: Frame) -> Frame:
        pass

    def with_column(self, expr) -> Frame:
        pass

    def limit(self, limit: int, offset: Optional[int] = None) -> Frame:
        pass

    def order_by(self, cols: List[Tuple[Column]]) -> Frame:
        pass

    def union_all(self, other: Frame) -> Frame:
        pass

    def intersect(self, other: Frame) -> Frame:
        pass

    def columns(self) -> List[Column]:
        pass

    def sql(self) -> str:
        pass



    


        
