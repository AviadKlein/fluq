from unittest import TestCase

from fluq._util import recursive_list_predicate_validation

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

