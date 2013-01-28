# Copyright (c) 2012-2013 SHIFT.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

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
