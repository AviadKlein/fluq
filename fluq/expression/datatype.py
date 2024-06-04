from __future__ import annotations

from abc import abstractclassmethod
from typing import Any, Callable, List, Dict, Tuple
from fluq.expression.base import Expression, SelectableExpression, TerminalExpression

class DataTypeExpression(Expression):
    """
    source: https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types"""
    
    @abstractclassmethod
    def symbol(cls) -> str:
        pass

    def tokens(self) -> List[str]:
        return [self.symbol()]
    
class ParameterizedDataType(DataTypeExpression):
    
    @abstractclassmethod
    def params_and_types(cls) -> Dict[str, Tuple[Any]]:
        """a dict of argument: (type, default value)"""
        pass

    def __init__(self, **kwargs):
        for kw in kwargs.keys():
            if kw not in self.params_and_types():
                raise SyntaxError(f"unrecognized argument: {kw}, supported are: {list(kwargs.keys())}")
        for key, _type in self.params_and_types().items():
            if key in kwargs:
                if not isinstance(kwargs[key], _type):
                    raise TypeError(f"argument '{key}' is supposed to be of type {_type}, got {type(kwargs[key])}")
                else:
                    self.__setattr__(key, kwargs[key])
            else:
                self.__setattr__(key, None)

    def paremeter_list(self) -> List[str]:
        result = []
        for key in self.params_and_types().keys():
            value = self.__getattribute__(key)
            if value is not None:
                result.append(str(value))
        return result
                

    def tokens(self) -> List[str]:
        result = self.symbol()
        param_list = self.paremeter_list()
        if len(param_list) > 0:
            result += f"({','.join(param_list)})"
        return [result]
        

class DataTypeWIthAliases(DataTypeExpression):

    @abstractclassmethod
    def aliases(cls) -> List[str]:
        pass

class BooleanDataType(DataTypeExpression, TerminalExpression):

    @classmethod
    def symbol(cls) -> str:
        return "BOOL"
    
class BytesDataType(ParameterizedDataType, TerminalExpression):

    @classmethod
    def params_and_types(cls) -> Dict[str, Tuple[Any, Any]]:
        return {'length': (int, None)}

    def __call__(self, length: int) -> BytesDataType:
        return BytesDataType(length=length)

    @classmethod
    def symbol(cls) -> str:
        return "BYTES"
    
class StringDataType(ParameterizedDataType, TerminalExpression):

    @classmethod
    def params_and_types(cls) -> Dict[str, Tuple[Any, Any]]:
        return {'length': (int, None)}

    @classmethod
    def symbol(cls) -> str:
        return "STRING"

class DateDataType(DataTypeExpression, TerminalExpression):

    @classmethod
    def symbol(cls) -> str:
        return "DATE"
    
class DateTimeDataType(DataTypeExpression, TerminalExpression):

    @classmethod
    def symbol(cls) -> str:
        return "DATETIME"
    
class GeographyDataType(DataTypeExpression, TerminalExpression):

    @classmethod
    def symbol(cls) -> str:
        return "GEOGRAPHY"
    
class IntervalDataType(DataTypeExpression, TerminalExpression):

    @classmethod
    def symbol(cls) -> str:
        return "INTERVAL"
    
class JSONDataType(DataTypeExpression, TerminalExpression):

    @classmethod
    def symbol(cls) -> str:
        return "JSON"
    
class INT64DataType(DataTypeWIthAliases, TerminalExpression):

    @classmethod
    def symbol(cls) -> str:
        return "INT64"
    
    @classmethod
    def aliases(cls) -> List[str]:
        return ['INT', 'SMALLINT', 'INTEGER', 'BIGINT', 'TINYINT', 'BYTEINT']
    
class NUMERICDataType(DataTypeWIthAliases, ParameterizedDataType, TerminalExpression):

    @classmethod
    def params_and_types(cls) -> Dict[str, Tuple[Any, Any]]:
        return {'precision': (int, 38), 'scale': (int, 9)}
    
    @classmethod
    def symbol(cls) -> str:
        return "NUMERIC"
    
    @classmethod
    def aliases(cls) -> List[str]:
        return ["DECIMAL"]

    def __call__(self, precision: int, scale: int) -> NUMERICDataType:
        return NUMERICDataType(precision=precision, scale=scale)

class BIGNUMERICDataType(DataTypeWIthAliases, ParameterizedDataType, TerminalExpression):

    @classmethod
    def params_and_types(cls) -> Dict[str, Tuple[Any, Any]]:
        return {'precision': (float, 76.76), 'scale': (int, 38)}

    @classmethod
    def symbol(cls) -> str:
        return "BIGNUMERIC"
    
    @classmethod
    def aliases(cls) -> List[str]:
        return ["BIGDECIMAL"]

    def __call__(self, precision: int, scale: int) -> BIGNUMERICDataType:
        return BIGNUMERICDataType(precision=precision, scale=scale)

class FLOAT64DataType(DataTypeExpression, TerminalExpression):

    @classmethod
    def symbol(cls) -> str:
        return "FLOAT64"
    
class TimeDataType(DataTypeExpression, TerminalExpression):

    @classmethod
    def symbol(cls) -> str:
        return "TIME"
    
class TimestampDataType(DataTypeExpression, TerminalExpression):

    @classmethod
    def symbol(cls) -> str:
        return "TIMESTAMP"
    
class CastExpression(SelectableExpression):

    def __init__(self, base: Expression, to: DataTypeExpression) -> None:
        assert isinstance(base, Expression)
        assert isinstance(to, DataTypeExpression)
        self.base = base
        self.to = to

    def tokens(self) -> List[str]:
        return ['CAST(', *self.base.tokens(), 'AS' ,*self.to.tokens(), ')']
    
    def sub_expressions(self) -> List[Expression]:
        return [self.base, self.to]
    
    


        


    



    
