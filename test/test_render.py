from unittest import TestCase
import textwrap

from fluq.render import *

def compare_str(a: str, b: str):
        assert isinstance(a, str)
        assert isinstance(b, str)
        ne = {}
        if len(a) < len(b):
            diff = len(b) - len(a)
            a += '\U0001F47F'*diff
        elif len(a) > len(b):
            diff = len(a) - len(b)
            b += '\U0001F47F'*diff
        for (i, (a_i, b_i)) in enumerate(zip(a,b)):
            if a_i != b_i:
                ne[i] = f"a: '{a_i}', b: '{b_i}'"
        if len(ne) > 0:
            ne = [str(k) for k in ne.items()]
            ne = '\n'.join(list(ne))
            raise AssertionError(f"""mismatches found: {ne}""")
        
class TestRendering(TestCase):

    def test_configs(self):
        tokens = ['SELECT', '*', 'FROM', 't1', 'WHERE', 't1.id', 'IS', 'NOT', 'NULL']
        result = SqlRenderer.render(tokens)
        self.assertEqual(result, 'SELECT * FROM t1 WHERE t1.id IS NOT NULL')

    def test_config1(self):
        tokens = ['SELECT', '*', 'FROM', 't1', 'WHERE', 't1.id', 'IS', 'NOT', 'NULL']
        select_config = RenderingContextConfig(
            break_on_change_context=True,
            increase_indent_in_context_change=True,
            indent_str='\t'
        )

        result = SqlRenderer.render(tokens, context2config={'SELECT': select_config})
        expected = textwrap.dedent("""SELECT\n\t * FROM t1 WHERE t1.id IS NOT NULL""")
        print(result)
        print(expected)
        self.assertEqual(result, expected)

    def test_config2(self):
        tokens = ['SELECT', '*', 'FROM', 't1', 'WHERE', 't1.id', 'IS', 'NOT', 'NULL']
        config = RenderingContextConfig(
            break_on_change_context=True,
            increase_indent_in_context_change=True,
            indent_str='  '
        )
        context2config = {
            'SELECT': config,
            'FROM': config,
            'WHERE': config
        }

        result = SqlRenderer.render(tokens, context2config=context2config)
        expected = """SELECT\n   *\nFROM\n   t1\nWHERE\n   t1.id IS NOT NULL"""
        print(result)
        print(expected)
        compare_str(result, expected)

    def test_subqueries(self):
        tokens = ['SELECT', 'a', ',', 'a+2', 'AS', 'g', 'FROM', '(', 'SELECT', 'a', 'FROM', 'c',')', 'AS', 't1', 'WHERE', 't1.id', 'IS', 'NOT', 'NULL']
        config = RenderingContextConfig(
            break_on_change_context=True,
            increase_indent_in_context_change=True,
            indent_str='  '
        )
        context2config = {
            'SELECT': config,
            'FROM': config,
            'WHERE': config
        }
        result = SqlRenderer.render(tokens, context2config=context2config)
        expected = """SELECT\n   a, a+2 AS g\nFROM\n   (\nSELECT\n   a\nFROM\n   c ) AS t1\nWHERE\n   t1.id IS NOT NULL"""
        self.assertEqual(result, expected)

    
    