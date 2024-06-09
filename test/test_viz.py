from unittest import TestCase

from fluq.viz import *


class TestNode(TestCase):

    def test_node_creation(self):
        node = Node(label='xx', shape='box', color='red')
        self.assertDictEqual(
            {'label': 'xx', 'shape': 'box', 'color': 'red', 'style': 'filled'}, node.dict)
    
    def test_color(self):
        node = Node(label='xx', shape='box', color=(255, 255, 0))
        self.assertEqual(node.color, '#FFFF00')



        