from __future__ import annotations

from abc import abstractclassmethod
from dataclasses import dataclass
from typing import List, Optional

from fluq.expression.base import Expression, TerminalExpression, SelectableExpression


class DateTimePartExpression(SelectableExpression, TerminalExpression):
    
    @abstractclassmethod
    def symbol(cls) -> str:
        pass

    def tokens(self) -> List[str]:
        return [self.symbol()]

class YearDateTimePart(DateTimePartExpression):

    @classmethod
    def symbol(cls) -> str:
        return "YEAR"
    
class IsoYearDateTimePart(DateTimePartExpression):

    @classmethod
    def symbol(cls) -> str:
        return "ISOYEAR"
    
class QuarterDateTimePart(DateTimePartExpression):

    @classmethod
    def symbol(cls) -> str:
        return "QUARTER"
    
class MonthDateTimePart(DateTimePartExpression):

    @classmethod
    def symbol(cls) -> str:
        return "MONTH"
    
class WeekDateTimePart(DateTimePartExpression):

    def __init__(self, weekday: Optional[str]=None):
        if weekday is not None:
            if weekday not in ('SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'):
                raise TypeError(f"wrong weekday, got '{weekday}'")
        self.weekday = weekday
        
    @classmethod
    def symbol(cls) -> str:
        return "WEEK"
    
    def tokens(self) -> List[str]:
        _base = super().tokens()[0]
        if self.weekday is None:
            return [_base]
        else:
            return [f"{_base}({self.weekday})"]
    

class IsoWeekDateTimePart(DateTimePartExpression):

    @classmethod
    def symbol(cls) -> str:
        return "ISOWEEK"

    
class DayDateTimePart(DateTimePartExpression):

    @classmethod
    def symbol(cls) -> str:
        return "DAY"
    
class HourDateTimePart(DateTimePartExpression):

    @classmethod
    def symbol(cls) -> str:
        return "HOUR"
    
class MinuteDateTimePart(DateTimePartExpression):

    @classmethod
    def symbol(cls) -> str:
        return "MINUTE"
    
class SecondDateTimePart(DateTimePartExpression):

    @classmethod
    def symbol(cls) -> str:
        return "SECOND"
    
class MilliSecondDateTimePart(DateTimePartExpression):

    @classmethod
    def symbol(cls) -> str:
        return "MILLISECOND"
    
class MicroSecondDateTimePart(DateTimePartExpression):

    @classmethod
    def symbol(cls) -> str:
        return "MICROSECOND"


class IntervalLiteralExpression(SelectableExpression):

    def __init__(self, duration: str | int,
                 datetime_part: DateTimePartExpression,
                 convert_to: Optional[DateTimePartExpression]=None):
        assert isinstance(duration, str | int)
        assert isinstance(datetime_part, DateTimePartExpression)
        if convert_to is not None:
            assert isinstance(convert_to, DateTimePartExpression)
        self.duration = duration
        self.datetime_part = datetime_part
        self.convert_to = convert_to

    def to(self, convert_to: DateTimePartExpression) -> IntervalLiteralExpression:
        if self.convert_to is not None:
            raise Exception()
        else:
            return IntervalLiteralExpression(self.duration, self.datetime_part, convert_to)

    def tokens(self) -> List[str]:
        resolved_duration = f"'{self.duration}'" if isinstance(self.duration, str) else str(self.duration)
        result = ['INTERVAL', resolved_duration, *self.datetime_part.tokens()]
        if self.convert_to is not None:
            result = [*result, 'TO', *self.convert_to.tokens()]
        return result
    
    def sub_expressions(self) -> List[Expression]:
        result = [self.datetime_part]
        if self.convert_to is not None:
            result.append(self.convert_to)
        return result

@dataclass
class OrderBySpecExpression(TerminalExpression):
    asc: bool=True
    nulls: str="FIRST"

    def __post_init__(self):
        assert isinstance(self.asc, bool)
        assert isinstance(self.nulls, str) and self.nulls in ("FIRST", "LAST")

    def tokens(self) -> List[str]:
        result = "ASC" if self.asc else "DESC"
        result += f" NULLS {self.nulls}"
        return [result]