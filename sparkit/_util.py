from typing import List, Callable, Any
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
