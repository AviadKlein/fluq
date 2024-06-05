from __future__ import annotations

from typing import Union, Tuple, Optional, List, Callable, Any
from copy import copy
from collections import Counter
from dataclasses import dataclass
import re



@dataclass
class TextRange:
    """Text ranges hold a start and end ints"""
    start: int
    end: int

    def __post_init__(self):
        assert isinstance(self.start, int), f"`start` must be an int, got {type(self.start)=}"
        assert isinstance(self.end, int), f"`end` must be an int, got {type(self.end)=}"
        assert self.start < self.end, f"`end` must be greater than `start`, got {self.start=}, {self.end=}"

    @property
    def slice(self) -> slice:
        return slice(self.start, self.end+1)
    
    @property
    def __len__(self) -> int:
        return self.end - self.start + 1
    
    @property
    def size(self) -> int:
        return len(self)
    
    def contains(self, index: int) -> bool:
        """returns a boolean whether the index is between start and end"""
        assert isinstance(index, int), f"`index` must be of type int, got {type(index)=}"
        return self.start <= index <= self.end
    
    def __add__(self, other: int) -> TextRange:
        assert isinstance(other, int), f"addition is only supported for int, got {type(other)=}"
        return TextRange(self.start+other, self.end+other)

    def shift(self, by: int) -> TextRange:
        """'shifts' the indices by stated amount, returns as a new object"""
        return self.__add__(by)

@dataclass
class StringLiteral:
    """an object that holds a literl str and the type of quotes that it is quoted by"""
    quotes: Tuple[str, str]
    value: str

    @property
    def key(self) -> str:
        return self.quotes[0]

    def __post_init__(self):
        assert self.key in QUOTES_DICT.keys(), f"unsupported LHS quote {self.key}"
        assert QUOTES_DICT[self.key] == self.quotes[1]
    

class ParseError(Exception):
    
    def __init__(self, message: str, s: Parsable) -> None:
        self.s = s
        super().__init__(message)
    


QUOTES_DICT = {
        '"':'"',
        "'":"'",
        '"""':'"""',
        "'''":"'''",
        'r"':'"',
        'r"""':'"""',
        "r'":"'",
        "r'''":"'''",
        "`":"`"
    }

class Parsable:

    def __init__(self, s: str):
        assert isinstance(s, str), f"`s` must be a str, got {type(s)=}"
        self.s = s # the original str
    
    @property
    def size(self) -> int:
        return len(self.s)
    
    def __len__(self) -> int:
        return self.size
    
    def __getitem__(self, index) -> Parsable:
        return Parsable(self.s[index])
    
    def index(self, substr: str, 
              offset: int=0) -> Optional[int]:
        """searches for substr within s and returns its index, returns None if not found
        offset is used to start the search from a specific index
        in case offset is not 0, the returned index will be 'offseted'
        """
        assert isinstance(substr, str), f"`substr` must be of type str, got {type(substr)=}"
        assert offset >= 0, f"`offset` can't be negative"
        assert offset <= len(self)-1, f"`offset` must be smaller then len - 1"

        try:
            return self.s[offset:].index(substr)
        except ValueError as ve:
            if "substring not found" in str(ve):
                return None
            else:
                raise ve
            
    def strip(self) -> Parsable:
        return Parsable(self.s.strip())
            
    def __repr__(self):
        _len = 10 if self.size > 10 else self.size
        return f"{self.__class__.__name__}('{self.s[:_len]}...')"
    
    def reversed(self) -> Parsable:
        "reverses the str, but flips the direction of parenthesis"
        lefts = set([i for i,c in enumerate(self.s) if c == '('])
        rights = set([i for i,c in enumerate(self.s) if c == ')'])
        new_s = list(copy(self.s))

        for i in lefts:
            new_s[i] = ')'
        for j in rights:
            new_s[j] = '('
        new_s.reverse()
        return Parsable(''.join(new_s))
    
    def mask(self, start: int, end: int, mask: str='\U0001F635') -> Parsable:
        assert isinstance(start, int)
        assert isinstance(end, int)
        assert start <= end
        
        result = []
        for i,c in enumerate(self.s):
            if start <= i <= end:
                result.append(mask)
            else:
                result.append(c)
        return Parsable(''.join(result))
 

def ensure_parsable(func: Callable) -> Callable:
    def wrapper(s: Union[str, Parsable], *args, **kwargs) -> Any:
        # Check if 's' is a string and convert it to 'Parsable' if necessary
        if isinstance(s, str):
            s = Parsable(s)
        elif not isinstance(s, Parsable):
            raise TypeError(f"`s` must be of type 'str' or 'Parsable', got {type(s)=}")
        # Call the original function with the new 's' and other arguments
        return func(s, *args, **kwargs)
    return wrapper

@ensure_parsable
def index_to_row_and_column(s: Union[Parsable, str], index: int) -> Tuple[int, int]:
    """given a str, will return the row/column representation of index"""
    assert isinstance(index, int), f"`i` must be an int"
    assert index >= 0, f"`i` must geq 0, got {index=}"
    assert index <= len(s) - 1, f"`i` must be less or equal to the length of `s`, got {len(s)=}, {index=}"
    row = 0
    column = 0
    i = 0
    while i < index:
        if s[i].s == '\n':
            row += 1
            column = 0
        else:
            column += 1
        i+=1
    return row, column

@ensure_parsable
def find_left_quote(s: Union[Parsable, str], offset: int=0) -> Optional[Tuple[int, str]]:
    """searches for a left quote and returns the index and type of quote
    if no quotes are found, returns a None"""
    left = {}
    for k,v in QUOTES_DICT.items():
        index = s.index(v, offset=offset)
        if index is not None:
            left[k] = index
        # out of those, find the minimum index, if the dict is empty, stop here
    if len(left) == 0:
        return None
    else:
        min_index = [(k, index, len(QUOTES_DICT[k])) for k, index in left.items()]
        min_index = sorted(min_index, key=lambda t: (t[1], -t[2]))
        quote, _index, _ = min_index[0]
    return _index, quote

@ensure_parsable
def find_enclosing_quote(s: Union[Parsable, str], left_quote: str, offset: int=0) -> Optional[int]:
    """searches for an enclosing quote and returns the index of it
    returns None, if nothing is found"""
    if isinstance(s, str):
        s = Parsable(s)
    assert left_quote in QUOTES_DICT.keys(), f"unrecognized left quote, {left_quote=}"
    right_quote = QUOTES_DICT[left_quote]
    search_offest = offset + len(left_quote)
    return s.index(right_quote, offset=search_offest)

@ensure_parsable
def find_string_literal(s: Union[Parsable, str], offset: int=0) -> Optional[Tuple[TextRange, StringLiteral]]:
    """searches for the first instance from the left of a string literal, returns None if not found"""
    
    # used when no enclosing quote is found to print this 
    # amount of characters in the ParseError message
    verbose_depth = 25 

    optional_result = find_left_quote(s, offset)
    if optional_result is None:
        return None
    else:
        left_index, left_quote = optional_result
        optional_right = find_enclosing_quote(s, left_quote, offset=offset+left_index)
        if optional_right is None:
            _right_hand = offset+left_index+verbose_depth
            raise ParseError(f"can't find enclosing quote for {s[(offset+left_index):_right_hand]}", s)
        else:
            start_index = offset + left_index
            end_index = offset + left_index + optional_right + len(QUOTES_DICT[left_quote])
            literal_start_index = offset + left_index + len(left_quote)
            literal_end_index = literal_start_index + optional_right
            literal = s[literal_start_index:(literal_end_index)].s # this needs to be of type `str`
            return (
                TextRange(start_index, end_index), 
                StringLiteral((left_quote, QUOTES_DICT[left_quote]), literal)
                )

@ensure_parsable
def parse_literals(s: Union[Parsable, str], offset: int=0) -> List[Tuple[TextRange, StringLiteral]]:
    """parses the entire string s and returns a list of Tuple[TextRange, StringLiteral]
    the list will be empty if none are found"""
    end = len(s) - 1
    results = []
    while offset < end:
        result = find_string_literal(s, offset)
        if result is None:
            break
        else:
            results.append(result)
            offset += (result[0].end + 1)
    return results

@ensure_parsable
def find_left_parenthesis(s: Union[Parsable, str], 
                          offset: int=0) -> Optional[int]:
    """returns the index of the first '(' found from the offset position, ignores string literals"""
    text_ranges = [text_range for text_range, _ in parse_literals(s)]
    
    for text_range in text_ranges:
        s = s.mask(text_range.start, text_range.end)

    result = s.index('(', offset=offset)
    return result
    
@ensure_parsable
def find_enclosing_parenthesis(s: Union[Parsable, str], 
                               offset: int=0, 
                               ) -> Optional[int]:
    """searches for enclosing ')', ignores literals
    offset needs to be the location of the left parenthesis"""
    
    text_ranges = [text_range for text_range, _ in parse_literals(s)]
    result = None
    depth = 0
    enumerated = enumerate(s.s)
    enumerated = list(enumerated)[offset:]
    enumerated = list(filter(lambda i: all([~text_range.contains(i) for text_range in text_ranges]), enumerated))

    for i, char in enumerated:
        if char == '(':
            depth += 1
        elif char == ')':
            if depth == 1:
                result = i
            else:
                depth -= 1
        else: # other characters
            pass
        
    return result

@ensure_parsable
def ensure_balanced_parenthesis(s: Union[Parsable, str], offset: int=0) -> bool:
    """checks if the number of '(' and ')' is balanced, ignores literals"""
    text_ranges = [text_range for text_range, _ in parse_literals(s[offset:])]
    cnt = []
    for i,char in enumerate(s[offset:].s):
        if any([tr.contains(i) for tr in text_ranges]):
            pass
        else:
            cnt.append(char)
    cnt = Counter(cnt)
    return cnt['('] == cnt[')']


@ensure_parsable
def parse_parenthesis(s: Union[Parsable, str], 
                      offset: int=0, 
                      level: int=0) -> List[Tuple[int, TextRange, Parsable]]:
    """returns a list of (depth, TextRange, Parsable)
    where depth is the depth of parenthesis
    text_range is a TextRange object of the parenthesis
    Parsable is the remaining str within the parenthesis
    
    for the str: "(the quick (brown (fox)))"
    the sub str "the quick" will be at level 0
    the sub str "brown" will be at level 1
    the sub str "fox" will be at level 2

    raises ParseError when parenthesis are not closed
    """
    # start parsing
    result = []
    left = find_left_parenthesis(s, offset)
    if left is None:
        pass
    else:
        left += offset
        right = find_enclosing_parenthesis(s[offset:], offset=left)
        if right is None:
            raise ParseError(f"can't find enclosing right parenthesis", s)
        else:
            
            # construct result
            text_range = TextRange(left, right)
            sub_parsable = s[text_range.slice]
            result += [(level, text_range, sub_parsable)]

            # recursively parse the remaining Parsable
            if len(sub_parsable) > 2:
                result += parse_parenthesis(sub_parsable[1:-1], level=level+1)
            result_cont = parse_parenthesis(s[right:], level=level)
            result_cont = [(a,b.shift(right),c) for a,b,c in result_cont]
            result += result_cont
    return result


@ensure_parsable
def parse_single_level(s: Union[Parsable, str], parsed_parenthesis: List[Tuple[int, TextRange, Parsable]]):
    level_0 = filter(lambda t: t[0] == 0, parsed_parenthesis)
    level_0 = list(level_0)
    for _, tr, _ in level_0:
        s = s.mask(tr.start, tr.end)
    head, *tail = re.split(r'(\s+|,|\(|\)|\[|\])', s.s)
    match head.upper():
        case 'SELECT':
            pass
        case 'WITH':
            pass
        case _:
            pass


    

    
    
