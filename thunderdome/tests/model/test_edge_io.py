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

from thunderdome.tests.base import BaseCassEngTestCase
from thunderdome.tests.models import TestModel, TestEdge


class TestEdgeIO(BaseCassEngTestCase):

    def setUp(self):
        super(TestEdgeIO, self).setUp()
        self.v1 = TestModel.create(count=8, text='a')
        self.v2 = TestModel.create(count=7, text='b')
        
    def test_model_save_and_load(self):
        """
        Tests that models can be saved and retrieved
        """
        e1 = TestEdge.create(self.v1, self.v2, numbers=3)
        
        edges = self.v1.outE()
        assert len(edges) == 1
        assert edges[0].eid == e1.eid
        
    def test_model_updating_works_properly(self):
        """
        Tests that subsequent saves after initial model creation work
        """
        e1 = TestEdge.create(self.v1, self.v2, numbers=3)

        e1.numbers = 20
        e1.save()
        
        edges = self.v1.outE()
        assert len(edges) == 1
        assert edges[0].numbers == 20

    def test_model_deleting_works_properly(self):
        """q
        Tests that an instance's delete method deletes the instance
        """
        e1 = TestEdge.create(self.v1, self.v2, numbers=3)
        
        e1.delete()
        edges = self.v1.outE()
        assert len(edges) == 0

    def test_reload(self):
        """ Tests that the reload method performs an inplace update of an instance's values """
        e1 = TestEdge.create(self.v1, self.v2, numbers=3)
        e2 = TestEdge.get_by_eid(e1.eid)
        e2.numbers = 5
        e2.save()

        e1.reload()
        assert e1.numbers == 5

