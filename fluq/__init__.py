# fluq/__init__.py

from .column import *
from .sql import *

__all__ = ['sql', 'column']

def __read_version():
    import os
    with open('./__version__.txt') as f:
        return f.read().strip()

__version__ = __read_version()
del(__read_version)