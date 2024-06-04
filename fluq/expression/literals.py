from __future__ import annotations

from abc import abstractclassmethod
from dataclasses import dataclass
from typing import Callable, List, Optional

from fluq.expression.base import Expression, TerminalExpression, SelectableExpression


class DateTimePart(TerminalExpression):
    
    @abstractclassmethod
    def symbol(cls) -> str:
        pass

    def tokens(self) -> List[str]:
        return [self.symbol()]

class YearDateTimePart(DateTimePart):

    @classmethod
    def symbol(cls) -> str:
        return "YEAR"
    
class QuarterDateTimePart(DateTimePart):

    @classmethod
    def symbol(cls) -> str:
        return "QUARTER"
    
class MonthDateTimePart(DateTimePart):

    @classmethod
    def symbol(cls) -> str:
        return "MONTH"
    
class WeekDateTimePart(DateTimePart):

    @classmethod
    def symbol(cls) -> str:
        return "WEEK"
    
class DayDateTimePart(DateTimePart):

    @classmethod
    def symbol(cls) -> str:
        return "DAY"
    
class HourDateTimePart(DateTimePart):

    @classmethod
    def symbol(cls) -> str:
        return "HOUR"
    
class MinuteDateTimePart(DateTimePart):

    @classmethod
    def symbol(cls) -> str:
        return "MINUTE"
    
class SecondDateTimePart(DateTimePart):

    @classmethod
    def symbol(cls) -> str:
        return "SECOND"


class IntervalLiteralExpression(SelectableExpression):

    def __init__(self, duration: str | int,
                 datetime_part: DateTimePart,
                 convert_to: Optional[DateTimePart]=None):
        assert isinstance(duration, str | int)
        assert isinstance(datetime_part, DateTimePart)
        if convert_to is not None:
            assert isinstance(convert_to, DateTimePart)
        self.duration = duration
        self.datetime_part = datetime_part
        self.convert_to = convert_to

    def to(self, convert_to: DateTimePart) -> IntervalLiteralExpression:
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