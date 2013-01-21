
from unittest import skip
from thunderdome import connection 
from thunderdome.tests.base import BaseCassEngTestCase


from thunderdome import gremlin
from thunderdome import models
from thunderdome.models import Edge, PaginatedVertex
from thunderdome import columns
import unittest



class TestPModel(PaginatedVertex):
    count   = columns.Integer()
    text    = columns.Text(required=False)

    
class TestPEdge(Edge):
    numbers = columns.Integer()



class PaginatedVertexTest(unittest.TestCase):
    def test_traversal(self):
        t = TestPModel.create()
        t2 = TestPModel.create()
        
        edges = []
        for x in range(5):
            edges.append(TestPEdge.create(t, t2, numbers=x))
        
        tmp = t.outV(page_num=1, per_page=2)
        assert len(tmp) == 2, len(tmp)
        
        tmp = t.outE(page_num=2, per_page=2)
        
        assert len(tmp) == 2, len(tmp)
        assert tmp[0].numbers == 2
        
        tmp = t.outE(page_num=3, per_page=2)
        assert len(tmp) == 1, len(tmp)
        
        # just to be sure
        all_edges = t.outV()
        assert len(all_edges) == 5
