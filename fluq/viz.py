from typing import Dict, Tuple
from dataclasses import dataclass, asdict

import pydot

from fluq.frame import Frame
from fluq.expression.base import Expression, TableNameExpression
from fluq.expression.clause import *

@dataclass
class Node:
    label: str
    shape: str
    color: str | Tuple[int, int, int]
    style: str='filled'

    def __post_init__(self):
        if isinstance(self.color, tuple):
            assert len(self.color) == 3
            assert all([0 <= _ <= 255 for _ in self.color])
            color = '#'
            for c in self.color:
                h = hex(c).upper()
                if len(h) == 3:
                    color += f"0{h[-1]}"
                elif len(h) == 4:
                    color += h[-2:]
                else:
                    raise Exception(f"weird hex, {c=} and {h=}")
            self.color = color

    @property
    def dict(self) -> Dict[str, str]:
        return asdict(self)


def expression_to_dot_node(expr: Expression) -> Node:
    match expr:
        case TableNameExpression(db_path):
            return Node(label=db_path, shape='Mrecord', color='blue')
        case PredicateClauseExpression(logical):
            return Node(
                label=(
                    '<'
                    '<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">'
                    '<TR><TD><B>Where</B></TD></TR>'
                    f'<TR><TD>{logical.sql.str}</TD></TR>'
                    '</TABLE>'
                    '>'
                    )
                ,shape='box', color='gray')
        case FromClauseExpression(_):
            return Node(label='FROM', shape='Mrecord', color='blue')
        case SelectClauseExpression(_):
            expression_entries = []
            for e, a in zip(expr.expressions, expr.aliases):
                entry = e.sql
                if a is not None:
                    entry += f' AS {a}'
                expression_entries.append(f'<TR><TD><B>{entry}</B></TD></TR>')
            return Node(
                label=
                    '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0"><TR><TD><B>Where</B></TD></TR>'\
                    +''.join(expression_entries)+'</TABLE>>',
                shape='box', color='orange'
                )
        

            

        
