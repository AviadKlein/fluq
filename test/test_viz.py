from unittest import TestCase

from fluq.sql import *
from fluq.sql import functions as fn
from fluq.viz import FrameGraph



class TestViz(TestCase):

    def test_viz(self):
        print(fn.sum(col("income")))
        query = (
            table("t1")
            .where(col("date") > '2024-01-01')
            .group_by(col("country"))
            .agg(fn.sum(col("income")))
            .order_by(col("sum_income").desc())
            .limit(50)
            )

        viz = FrameGraph(query)
        # viz.plot()