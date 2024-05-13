from abc import ABC, abstractmethod
from dataclasses import dataclass


class DataType(ABC):

    @abstractmethod
    def catalogName(self) -> str:
        pass

    def __str__(self) -> str:
        return f'DataType <{self.catalogName}>'
    
    def __hash__(self) -> int:
        return hash(self.catalogName)


class BooleanType(DataType):

    @property
    def catalogName(self) -> str:
        return "bool"


class IntType(DataType):
    
    @property
    def catalogName(self) -> str:
        return "int"
    

class FloatType(DataType):

    @property
    def catalogName(self) -> str:
        return "float"
    

class ArrayType(DataType):

    def __init__(self, element_type: DataType):
        super().__init__()
        self.element_type = element_type

    @property
    def catalogName(self) -> str:
        return f"array[{self.element_type.catalogName}]"
    




