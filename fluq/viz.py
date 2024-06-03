import networkx as nx
import matplotlib.pyplot as plt

from fluq.frame import Frame
from fluq.expression.base import *
from fluq.expression.query import *


class FrameGraph:

    def __init__(self, frame: Frame) -> None:
        self.g = nx.DiGraph()
        self.frame = frame
        self.expr = self.frame._get_expr()
        match self.expr:
            case QueryExpression(from_, where, group_by, select, having, qualify, order_by, limit):
                if from_ is not None:
                    self.g.add_node(hash(from_), label='FROM')
                if where is not None:
                    self.g.add_node(hash(where), label='WHERE')
                    self.g.add_edge(hash(from_), hash(where))
                if group_by is not None:
                    self.g.add_node(hash(group_by), label='GROUP BY')
                    source_id = hash(where) if where is not None else hash(from_)
                    self.g.add_edge(source_id, hash(group_by))
                
                self.g.add_node(hash(select), label='SELECT')
                if group_by is not None:
                    self.g.add_edge(hash(group_by), hash(select))
                elif where is not None:
                    self.g.add_edge(hash(where), hash(select))
                elif from_ is not None:
                    self.g.add_edge(hash(from_), hash(select))
                else:
                    pass

                if order_by is not None:
                    self.g.add_node(hash(order_by), label='ORDER BY')
                    self.g.add_edge(hash(select), hash(order_by))
                if limit is not None:
                    self.g.add_node(hash(limit), label='LIMIT')
                    source_id = hash(order_by) if order_by is not None else hash(select)
                    self.g.add_edge(source_id, hash(order_by))

    def plot(self):
        nx.draw(self.g, with_labels=True, node_color='lightblue', edge_color='gray', node_size=700, font_size=4)
        plt.show()
        
