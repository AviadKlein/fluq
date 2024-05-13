from __future__ import annotations

from typing import Union, Optional, List, Tuple, Any
from collections import OrderedDict
from dataclasses import dataclass

import pandas as pd

from datatype import DataType
from expression import ValidName
from column import Column



Identifier = Union[str, ValidName, Column]
TableIdentifier = Union[str, ValidName]

class Frame:

    def __init__(self, **kwargs):
        pass

    @classmethod
    def from_table_identifier(cls, table_identifier: TableIdentifier) -> Frame:
        pass
    
    @classmethod
    def from_schema(cls, schema: OrderedDict[ValidName, DataType]) -> Frame:
        pass
    
    @classmethod
    def from_db(cls, full_path) -> Frame:
        pass

    @classmethod
    def from_pandas(cls, df: pd.DataFrame) -> Frame:
        pass

    def from_(self) -> From:
        pass

    def select(self, *args) -> Frame:
        pass

    def where(self, predicate) -> Frame:
        pass
    
    def join(self, other: Frame, join_type, by) -> Frame:
        pass

    def with_column(self, expr) -> Frame:
        pass

    def limit(self, limit: int, offset: Optional[int] = None) -> Frame:
        pass

    def order_by(self, cols: List[Tuple[Column]]) -> Frame:
        pass

    def union_all(self, other: Frame) -> Frame:
        pass

    def columns(self) -> List[Column]:
        pass

    def group_by(self, cols: List):
        pass

    def to_sql(self) -> str:
        pass



    


        
