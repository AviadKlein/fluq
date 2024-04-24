from typing import Union, Tuple, Optional, List, Callable, Any
from dataclasses import dataclass

@dataclass
class Block:
    pass

@dataclass
class Expression(Block):
    pass


@dataclass
class TextRange:
    start: int
    end: int

    def __post_init__(self):
        assert isinstance(self.start, int), f"`start` must be an int, got {type(self.start)=}"
        assert isinstance(self.end, int), f"`end` must be an int, got {type(self.end)=}"
        assert self.start < self.end, f"`end` must be greater than `start`, got {self.start=}, {self.end=}"

    @property
    def slice(self) -> Tuple[int, int]:
        return slice(self.start, self.end+1)
    
    @property
    def __len__(self) -> int:
        return self.end - self.start + 1
    
    @property
    def size(self) -> int:
        return len(self)

@dataclass
class StringLiteral(Expression):
    quotes: Tuple[str, str]
    value: str

    @property
    def original_size(self):
        return sum()

@dataclass
class Query(Block):
    FROM: Expression
    WHERE: Expression
    GROUP_BY: Expression
    SELECT: Expression
    HAVING: Expression
    QUALIFY: Expression
    ORDER_BY: Expression
    LIMIT: int
    OFFSET: int

class ParseError(Exception):
    
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

QUOTES_DICT = {
        '"':'"',
        "'":"'",
        '"""':'"""',
        "'''":"'''",
        'r"':'"',
        'r"""':'"""',
        "r'":"'",
        "r'''":"'''"
    }

class Parsable:

    def __init__(self, s: str):
        assert isinstance(s, str), f"`s` must be a str, got {type(s)=}"
        assert len(s) > 0, f"`s` can't be an empty str"
        self.s = s
        self.enumerated = enumerate(s)
    
    @property
    def size(self) -> int:
        return len(self.s)
    
    def __len__(self) -> int:
        return self.size
    
    def __getitem__(self, index):
        return self.s[index]
    
    def index(self, substr: str, offset: int=0) -> Optional[int]:
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
        

def ensure_parsable(func: Callable) -> Callable:
    def wrapper(s: Union[str, Parsable], *args, **kwargs) -> Any:
        # Check if 's' is a string and convert it to 'Parsable' if necessary
        if isinstance(s, str):
            s = Parsable(s)
        elif not isinstance(s, Parsable):
            raise TypeError(f"Argument 's' must be of type 'str' or 'Parsable', got {type(s)=}")
        # Call the original function with the new 's' and other arguments
        return func(s, *args, **kwargs)
    return wrapper

@ensure_parsable
def index_to_row_and_column(s: Union[Parsable, str], index: int) -> Tuple[int, int]:
    """given a str, will return the row/column representation of the index"""
    assert isinstance(index, int), f"`i` must be an int"
    assert index >= 0, f"`i` must geq 0, got {index=}"
    assert index <= len(s) - 1, f"`i` must be less or equal to the length of `s`, got {len(s)=}, {index=}"
    row = 0
    column = 0
    i = 0
    while i < index:
        if s[i] == '\n':
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
            raise ParseError(f"can't find enclosing quote for {s[(offset+left_index):_right_hand]}")
        else:
            start_index = offset + left_index
            end_index = offset + left_index + optional_right + len(QUOTES_DICT[left_quote])
            literal_start_index = offset + left_index + len(left_quote)
            literal_end_index = literal_start_index + optional_right
            literal = s[literal_start_index:(literal_end_index)]
            return (
                TextRange(start_index, end_index), 
                StringLiteral((left_quote, QUOTES_DICT[left_quote]), literal)
                )

@ensure_parsable
def parse_literals(s: Union[Parsable, str], offset=0) -> List[Tuple[TextRange, StringLiteral]]:
    """parses the entire string s and returns a list of Tuple[TextRange, StringLiteral]
    the list will be empty if none are found"""
    pass
