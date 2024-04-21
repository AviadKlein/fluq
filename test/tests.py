from unittest import TestCase

from parse import *

class TestParsing(TestCase):

    def test_parsable_len(self):
        s = "the quick brown fox"
        result = Parsable(s)
        self.assertEqual(result.size, 19)
        self.assertEqual(result.size, len(result))

    def test_parsable_getitem(self):
        s = "the quick brown fox"
        result = Parsable(s)
        self.assertEqual(result[0], 't')
        self.assertEqual(result[1], 'h')
        self.assertEqual(result[:3], 'the')
        self.assertEqual(result[-3:], 'fox')
        self.assertEqual(result[-1], 'x')
        self.assertEqual(result[-3], 'f')

    def test_parsable_init(self):
        with self.assertRaises(AssertionError) as cm:
            Parsable(44)
        self.assertTrue("`s` must be a str, got type(s)=<class 'int'" in str(cm.exception))
    
        with self.assertRaises(AssertionError) as cm:
            Parsable("")
        self.assertTrue("`s` can't be an empty str" in str(cm.exception))

    def test_index_to_row_and_column(self):
        s = "the quick brown fox"
        f = index_to_row_and_column
        self.assertEqual(f(s, 0), (0, 0))
        self.assertEqual(f(s, 4), (0, 4))

        s = """the\nquick\nbrown\nfox"""
        self.assertEqual(f(s, 3), (0, 3)) # this is the space between 'fox' and 'quick'
        self.assertEqual(f(s, 4), (1, 0)) # this is the line break '\n'
        self.assertEqual(f(s, 5), (1, 1)) # this is location of 'q'
        self.assertEqual(f(s, 10), (2, 0)) # this is location of 'b'
        self.assertEqual(f(s, 12), (2, 2)) # this is location of 'o'

    def test_parsable_index(self):
        s = "the quick brown fox"
        p = Parsable(s)
        self.assertEqual(p.index('t'), 0)
        self.assertEqual(p.index('the'), 0)
        self.assertEqual(p.index('qui'), 4)

        self.assertIsNone(p.index('5'))

    def test_parsable_index_offset(self):
        self.assertEqual(Parsable('aaaa').index('a'), 0)
        self.assertEqual(Parsable('aaaa').index('a',1), 0)
        self.assertEqual(Parsable('aaaa').index('a',2), 0)
        self.assertEqual(Parsable('aaaa').index('a',3), 0)

        self.assertEqual(Parsable('abab').index('a'), 0)
        self.assertEqual(Parsable('abab').index('a', 1), 1)
        self.assertEqual(Parsable('abab').index('b', 1), 0)
        self.assertEqual(Parsable('abab').index('b', 2), 1)

        self.assertEqual(Parsable('aaaa').index('a', 3), 0)

        with self.assertRaises(AssertionError) as cm:
            Parsable('aaaa').index('a', 4)
        self.assertTrue("`offset` must be smaller then len - 1" in str(cm.exception))

    def test_find_left_quote(self):
        s = [
            'he said """boo hoo""" to her face',
            'he said """  """ to her face',
            """quote 'un"qu""ote'""",
            """'''Title:"Boy"'''""",
            '''Title:"Boy"''',
            'Title: "Boy"',
        ]
        e = [
            (8, '"""'),
            (8, '"""'),
            (6, "'"),
            (0, "'''"),
            (6, '"'),
            (7, '"')
        ]
        for s_i, e_i in zip(s,e):
            try:
                self.assertEqual(find_left_quote(s_i), e_i)
            except AssertionError as ae:
                print(f"{s_i=}")
                raise ae
            
    def test_find_enclosing_quote(self):
        strs = [
            'he said """boo hoo""" to her face',
            'he said """  """ to her face',
            """quote 'un"qu""ote'""",
            """'''Title:"Boy"'''""",
            '''Title:"Boy"''',
            'Title: "Boy"',
        ]
        inputs = [
            (8, '"""'),
            (8, '"""'),
            (6, "'"),
            (0, "'''"),
            (6, '"'),
            (7, '"')
        ]
        expected = [7, 2, 10, 11, 3, 3]
        for s_i, (offset, left_quote), exp in zip(strs,inputs, expected):
            try:
                result = find_enclosing_quote(s_i, left_quote, offset)
                self.assertEqual(result, exp)
            except AssertionError as ae:
                print(f"{s_i=}")
                raise ae
            
    def test_find_string_literal(self):
        s = Parsable("select * from gg where index='done' and date >= '2023-01-01' ")
        ((start, end), literal) = find_string_literal(s)
        self.assertEqual(start, 29)
        self.assertEqual(end, 35)
        self.assertEqual(literal.value, "done")
        self.assertEqual(literal.quotes, ("'", "'"))
        self.assertEqual(s[start:end], "'done'")

        s = Parsable("""select * from gg where index='do"ne' and date >= '2023-01-01' """)
        ((start, end), literal) = find_string_literal(s)
        self.assertEqual(start, 29)
        self.assertEqual(end, 36)
        self.assertEqual(literal.value, 'do"ne')
        self.assertEqual(literal.quotes, ("'", "'"))
        self.assertEqual(s[start:end], """'do"ne'""")


        s = Parsable("""select * from gg where index='' and date >= '2023-01-01' """)
        ((start, end), literal) = find_string_literal(s)
        self.assertEqual(start, 29)
        self.assertEqual(end, 31)
        self.assertEqual(literal.value, '')
        self.assertEqual(literal.quotes, ("'", "'"))
        self.assertEqual(s[start:end], """''""")
