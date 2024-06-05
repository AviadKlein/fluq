from unittest import TestCase

from fluq.parse.parse import *
from fluq.expression.clause import SelectClauseExpression
from fluq.expression.selectable import LiteralExpression

class TestParsingBase(TestCase):

    def test_text_range_init(self):
        tr = TextRange(0, 1)

        with self.assertRaises(AssertionError) as cm:
            TextRange(0.1, 1)
        self.assertTrue("`start` must be an int, got type(self.start)=<class 'float'>" in str(cm.exception))

        with self.assertRaises(AssertionError) as cm:
            TextRange(0, 1.2)
        self.assertTrue("`end` must be an int, got type(self.end)=<class 'float'>" in str(cm.exception))

        with self.assertRaises(AssertionError) as cm:
            TextRange(0, 0)
        self.assertTrue("`end` must be greater than `start`, got self.start=0, self.end=0" in str(cm.exception))

    def test_text_range_slice(self):
        tr = TextRange(3,5)
        self.assertEqual('abcdefg'[tr.slice], 'def')

        tr = TextRange(1,2)
        self.assertEqual('abcdefg'[tr.slice], 'bc')

    def test_text_range_add(self):
        tr = TextRange(3,5)
        result = tr + 3
        self.assertEqual(result.start, 6)
        self.assertEqual(result.end, 8)

        result = tr.shift(4)
        self.assertEqual(result.start, 7)
        self.assertEqual(result.end, 9)

    def test_parsable_len(self):
        s = "the quick brown fox"
        result = Parsable(s)
        self.assertEqual(result.size, 19)
        self.assertEqual(result.size, len(result))

    def test_parsable_getitem(self):
        s = "the quick brown fox"
        result = Parsable(s)
        self.assertEqual(result[0].s, 't')
        self.assertEqual(result[1].s, 'h')
        self.assertEqual(result[:3].s, 'the')
        self.assertEqual(result[-3:].s, 'fox')
        self.assertEqual(result[-1].s, 'x')
        self.assertEqual(result[-3].s, 'f')

    def test_parsable_init(self):
        with self.assertRaises(AssertionError) as cm:
            Parsable(44)
        self.assertTrue("`s` must be a str, got type(s)=<class 'int'" in str(cm.exception))
    
        p = Parsable("")
        self.assertEqual(len(p), 0)

    def test_parsable_reversed(self):
        p = Parsable('start (here) end (there)')
        result = p.reversed()
        self.assertEqual(result.s, "(ereht) dne (ereh) trats")

    def test_parsable_mask(self):
        p = Parsable('something to mask something to keep')
        result = p.mask(13,16)
        self.assertEqual(len(result), len(p))
        self.assertEqual(result.s, "something to 😵😵😵😵 something to keep")        

    def test_ensure_parsable(self):
        @ensure_parsable
        def f(s: Union[Parsable, str]):
            return s
        
        with self.assertRaises(TypeError) as cm:
            f(1)
        print(str(cm.exception))
        self.assertTrue("`s` must be of type 'str' or 'Parsable', got type(s)=<class 'int'>" in str(cm.exception))

        self.assertTrue(isinstance(f('a'), Parsable))
        

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

    def test_parsable_index_substr_at_offset(self):
        self.assertEqual(Parsable('abcd').index('a', 0), 0)
        self.assertEqual(Parsable('abcd').index('b', 1), 0)
        self.assertEqual(Parsable("""select * from gg where index='' and date >= '2023-01-01' """).index("'", 30), 0)

    def test_find_left_quote(self):
        s = [
            'he said """boo hoo""" to her face',
            'he said """  """ to her face',
            """quote 'un"qu""ote'""",
            """'''Title:"Boy"'''""",
            '''Title:"Boy"''',
            'Title: "Boy"',
            """select * from gg where index='' and date >= '2023-01-01' """,
            "   `ggg`"
        ]
        e = [
            (8, '"""'),
            (8, '"""'),
            (6, "'"),
            (0, "'''"),
            (6, '"'),
            (7, '"'),
            (29,"'"),
            (3, "`")
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
            """select * from gg where index='' and date >= '2023-01-01' """,
            "  `ggg`"
        ]
        inputs = [
            (8, '"""'),
            (8, '"""'),
            (6, "'"),
            (0, "'''"),
            (6, '"'),
            (7, '"'),
            (29,"'"),
            (2, "`")
        ]
        expected = [7, 2, 10, 11, 3, 3, 0, 3]
        assert len(expected) == len(inputs)
        assert len(strs) == len(inputs)
        for s_i, (offset, left_quote), exp in zip(strs, inputs, expected):
            try:
                result = find_enclosing_quote(s_i, left_quote, offset)
                self.assertEqual(result, exp)
            except AssertionError as ae:
                print(f"{s_i=}")
                raise ae
            
    def test_find_string_literal(self):
        s = Parsable("select * from gg where index='done' and date >= '2023-01-01' ")
        (trange, literal) = find_string_literal(s)
        self.assertEqual(trange.start, 29)
        self.assertEqual(trange.end, 34)
        self.assertEqual(literal.value, "done")
        self.assertEqual(literal.quotes, ("'", "'"))
        self.assertEqual(s[trange.slice].s, "'done'")

        s = Parsable("""select * from gg where index='do"ne' and date >= '2023-01-01' """)
        (trange, literal) = find_string_literal(s)
        self.assertEqual(trange.start, 29)
        self.assertEqual(trange.end, 35)
        self.assertEqual(literal.value, 'do"ne')
        self.assertEqual(literal.quotes, ("'", "'"))
        self.assertEqual(s[trange.slice].s, """'do"ne'""")


        s = Parsable("""select * from gg where index='' and date >= '2023-01-01' """)
        (trange, literal) = find_string_literal(s)
        self.assertEqual(trange.start, 29)
        self.assertEqual(trange.end, 30)
        self.assertEqual(literal.value, '')
        self.assertEqual(literal.quotes, ("'", "'"))
        self.assertEqual(s[trange.slice].s, """''""")

    def test_parse_litarals(self):
        s = """hello mr. 'di"n"gy' my name is 'ro""ber'!"""
        result = parse_literals(s)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][1].value, 'di"n"gy')
        self.assertEqual(result[1][1].value, 'ro""ber')

        s = """number '1', number '''2''', number r'''3'''"""
        result = parse_literals(s)
        for t in result:
            print(f"\n{t}")
        self.assertEqual(len(result), 3)
        self.assertEqual(result[2][1].quotes, ("'''", "'''"))

        
        s = """number r'''3"""
        with self.assertRaises(ParseError) as cm:
            parse_literals(s)
        self.assertTrue("can't find enclosing quote for" in str(cm.exception))

    def test_find_left_parenthesis_ignore_literals(self):
        s = "start here '(ignore this)' end here"
        result = find_left_parenthesis(s)
        self.assertIsNone(result)
    
    def test_find_left_parenthesis(self):
        result = find_left_parenthesis("start (here) and end (there)")
        self.assertEqual(result, 6)

        result = find_left_parenthesis("start '(here)' and end (there)")
        self.assertEqual(result, 23)

        result = find_left_parenthesis("start '(here)' and end '(there)' and (tither) too")
        self.assertEqual(result, 37)

    def test_find_left_parenthesis_offset(self):
        result1 = find_left_parenthesis("start (here) and end (there)", offset=0)
        self.assertEqual(result1, 6)
        result2 = find_left_parenthesis("start (here) and end (there)", offset=result1+1)
        self.assertEqual(result2, 14)
        self.assertEqual(result1+result2+1, 21)

    def test_find_enclosing_parenthesis(self):
        s = "start (here) and end (there)"
        offset = find_left_parenthesis(s)
        self.assertEqual(offset, 6)
        result = find_enclosing_parenthesis(s, offset=offset)
        self.assertEqual(result, 11)

        
        offset = find_left_parenthesis(s, offset=result) + result
        result = find_enclosing_parenthesis(s, offset=offset)
        self.assertEqual(offset, 21)
        self.assertEqual(result, 27)

    def test_find_enclosing_parenthesis_multiple(self):
        s = "(((((((horse)))))))"
        offset = find_left_parenthesis(s)
        result = find_enclosing_parenthesis(s, offset=offset)
        self.assertEqual(offset, 0)
        self.assertEqual(result, 18)

        s = "((((horse)))" # 1 is missing
        offset = find_left_parenthesis(s)
        result = find_enclosing_parenthesis(s, offset=offset)
        self.assertEqual(offset, 0)
        self.assertIsNone(result)

    def test_ensure_balanced_parenthesis(self):
        s = [
            "just a sentence",
            "a (sentence) with (balanced (paren)thesis)",
            "another )balanced( senten)c(e",
            "an ((unbalanced) sentence",
            "start (here)"
        ]
        expected = [True, True, True, False, True]
        for s_i, e_i in zip(s, expected):
            self.assertEqual(ensure_balanced_parenthesis(s_i), e_i, msg=s_i)

    def test_parse_parenthesis_exception_right(self):
        s = [
                "start (here", 
                "start (here ()",
            ]
        for s_i in s:
            with self.assertRaises(ParseError, msg=f"No ParseError was raised on '{s_i}'") as cm:
                parse_parenthesis(s_i)
            print(str(cm.exception))
            self.assertTrue("can't find enclosing right parenthesis" in str(cm.exception))
    
    def test_parse_parenthesis_0(self):
        s = "start here"
        result = parse_parenthesis(s)

        self.assertTrue(isinstance(result, list))
        self.assertEqual(len(result), 0)

        s = "start here '(ignore this)' end here"
        result = parse_parenthesis(s)

        self.assertTrue(isinstance(result, list))
        self.assertEqual(len(result), 0)
    
    def test_parse_parenthesis_1(self):
        s = "start (here)"
        result = parse_parenthesis(s)

        for e in result:
            print(e)
        
        self.assertEqual(result[0][0], 0)
        self.assertEqual(result[0][1], TextRange(6, 11))
        self.assertEqual(result[0][2].s, '(here)')
        
        self.assertEqual(len(result), 1)

    def test_parse_parenthesis_2(self):
        s = "start (here) and end (there)"
        result = parse_parenthesis(s)

        for e in result:
            print(e)
        
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0][0], 0)
        self.assertEqual(result[0][1], TextRange(6, 11))
        self.assertEqual(result[0][2].s, '(here)')

        self.assertEqual(result[1][0], 0)
        self.assertEqual(result[1][1], TextRange(21, 27))
        self.assertEqual(result[1][2].s, '(there)')

    def test_parse_parenthesis_3(self):
        s = "start (here) and end (there) and (yonder)"
        result = parse_parenthesis(s)
        
        self.assertEqual(len(result), 3)

        self.assertEqual(result[0][0], 0)
        self.assertEqual(result[0][1], TextRange(6, 11))
        self.assertEqual(result[0][2].s, '(here)')

        self.assertEqual(result[1][0], 0)
        self.assertEqual(result[1][1], TextRange(21, 27))
        self.assertEqual(result[1][2].s, '(there)')

        self.assertEqual(result[2][0], 0)
        self.assertEqual(result[2][1], TextRange(33, 40))
        self.assertEqual(result[2][2].s, '(yonder)')

    def test_parse_parenthesis_nested(self):
        s = "start (here, continue (here)) and end (there, not (here or (tither)))"
        result = parse_parenthesis(s)

        self.assertEqual(len(result), 5)
        self.assertCountEqual(map(lambda t: t[0], result), [0,0,1,1,2])
    
        self.assertEqual(result[0][0], 0)
        self.assertEqual(result[0][1], TextRange(6,28))

        self.assertEqual(result[1][0], 1)
        self.assertEqual(result[1][1], TextRange(15,20))

        self.assertEqual(result[2][0], 0)
        self.assertEqual(result[2][1], TextRange(38,68))

        self.assertEqual(result[3][0], 1)
        self.assertEqual(result[3][1], TextRange(39,56))

        self.assertEqual(result[4][0], 2)
        self.assertEqual(result[4][1], TextRange(36,43))

class TestParseQueries(TestCase):
    
    def test_parse_single_level(self):
        s = """select 1,2,3"""
        result = parse_single_level(s, parsed_parenthesis=parse_parenthesis(s))
        print(result)

    def test_simple_select_no_from(self):
        s = """select 1,2,3"""
        expected = SelectClauseExpression(
            expressions=[LiteralExpression(1), LiteralExpression(2), LiteralExpression(3)],
            aliases=[None, None, None]
            )
        self.fail("wip")
        
