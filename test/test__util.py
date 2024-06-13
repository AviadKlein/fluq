from unittest import TestCase

from fluq._util import recursive_list_predicate_validation, resolve_literal_to_str

class UtilTest(TestCase):

    def test_recursive_type_check(self):
        predicate = lambda x: isinstance(x, int)
        lst = []
        self.assertTrue(recursive_list_predicate_validation(lst, predicate))

        lst = [1,2,3]
        self.assertTrue(recursive_list_predicate_validation(lst, predicate))

        lst = [[1,2,3]]
        self.assertTrue(recursive_list_predicate_validation(lst, predicate))

        lst = [[1,2,3, [4,5,6], [[[6]]]], 5, -5]
        self.assertTrue(recursive_list_predicate_validation(lst, predicate))

        lst = [[1,2,3, [4,"5",6], [[[6]]]], 5, -5]
        self.assertFalse(recursive_list_predicate_validation(lst, predicate))

    def test_resolve_literal_to_str(self):
        inputs = [True, False, 1, -1, 1e3, 4.5, 'gaga']
        expected = ['TRUE', 'FALSE', '1', '-1', '1000.0', '4.5', "'gaga'"]
        for i, e in zip(inputs, expected):
            self.assertEqual(resolve_literal_to_str(i), e)
        

