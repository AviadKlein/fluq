from typing import List, Callable, Any, Optional
import json


def is_valid_json(s: str) -> bool:
    try:
        json.loads(s)
    except json.JSONDecodeError:
        return False
    else:
        return True


def recursive_list_predicate_validation(obj: List, predicate: Callable[[Any], bool]):
    result = True
    for elem in obj:
        if isinstance(elem, list):
            result &= recursive_list_predicate_validation(elem, predicate)
        elif predicate(elem):
            pass
        else:
            result = False
    return result


def _copy_doc(source, preamble: Optional[str]=None):
    """decorator to copy __doc__ str between methods"""
    def decorator(target):
        target.__doc__ = source.__doc__
        if preamble is not None:
            target.__doc__ = f"{preamble}\n\n{target.__doc__}"
        return target
    return decorator

def resolve_literal_to_str(value: int | float | bool | str) -> str:
    """helper method to convert a pyton primitive into a SQL-like str
    
    Example:
        print(resolve_literal_to_str(True)) # output: TRUE
    """
    sql_value = None
    if isinstance(value, bool):
        sql_value = str(value).upper()
    elif isinstance(value, str):
        sql_value = f"'{value}'"
    elif isinstance(value, (float, int)):
        sql_value = str(value)
    else:
        raise TypeError(f"supported literal types are: int | float | bool | str, got {type(value)=}")
    return sql_value
