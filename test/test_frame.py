from unittest import TestCase

from frame import *

class TestFrame(TestCase):
    
    def test_table_construction_method(self):
        frame = table("a")
        self.assertEqual(frame.sql, """SELECT *\nFROM a""")
        
    def test_copy_doc(self):
        self.assertEqual(table("a").filter.__doc__.split('\n')[0], "An alias for 'where'")

    def test_frame_alias(self):
        frame = table("a")
        self.assertEqual(frame.sql, """SELECT *\nFROM a""")
        # has no alias
        self.assertIsNone(frame.alias)

        frame = frame.as_("t1")

        # doesn't change the sql
        self.assertEqual(frame.sql, """SELECT *\nFROM a""")
        # but has an alias
        self.assertEqual(frame.alias, "t1")

    def test_frame_alias_bad_name(self):
        with self.assertRaises(Exception) as cm:
            table("a").as_("23abs")
        self.assertTrue("illegal name, due to bad characters in these locations" in str(cm.exception))

    def test_frame_alias_setter(self):
        with self.assertRaises(SyntaxError) as cm:
            frame = table("a").as_("t1")   
            frame.alias = "t2"
        self.assertEqual("can't assign alias, use the as_ method instead", str(cm.exception))

    def test_frame_is_select_all(self):
        frame = table("a")
        self.assertTrue(frame._is_select_all())

        frame = frame.select("*")
        self.assertTrue(frame._is_select_all())

        frame = table("a").select("a", "b", "c")
        self.assertFalse(frame._is_select_all())
