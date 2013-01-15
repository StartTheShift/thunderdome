from unittest import skip
from thunderdome.tests.base import BaseCassEngTestCase
from thunderdome.tests.models import TestModel, TestEdge

from thunderdome.models import Edge, Vertex
from thunderdome import columns


class OtherTestModel(Vertex):
    count = columns.Integer()
    text  = columns.Text()

class OtherTestEdge(Edge):
    numbers = columns.Integer()


class TestVertexIO(BaseCassEngTestCase):

    def test_model_save_and_load(self):
        """
        Tests that models can be saved and retrieved
        """
        tm0 = TestModel.create(count=8, text='123456789')
        tm1 = TestModel.create(count=9, text='456789')
        tms = TestModel.all([tm0.vid, tm1.vid])

        assert len(tms) == 2
       
        for cname in tm0._columns.keys():
            self.assertEquals(getattr(tm0, cname), getattr(tms[0], cname))
            
        tms = TestModel.all([tm1.vid, tm0.vid])
        assert tms[0].vid == tm1.vid 
        assert tms[1].vid == tm0.vid 
            
    def test_model_updating_works_properly(self):
        """
        Tests that subsequent saves after initial model creation work
        """
        tm = TestModel.create(count=8, text='123456789')

        tm.count = 100
        tm.save()

        tm.count = 80
        tm.save()

        tm.count = 60
        tm.save()

        tm.count = 40
        tm.save()

        tm.count = 20
        tm.save()

        tm2 = TestModel.get(tm.vid)
        self.assertEquals(tm.count, tm2.count)

    def test_model_deleting_works_properly(self):
        """
        Tests that an instance's delete method deletes the instance
        """
        tm = TestModel.create(count=8, text='123456789')
        vid = tm.vid
        tm.delete()
        with self.assertRaises(TestModel.DoesNotExist):
            tm2 = TestModel.get(vid)

    def test_reload(self):
        """ Tests that and instance's reload method does an inplace update of the instance """
        tm0 = TestModel.create(count=8, text='123456789')
        tm1 = TestModel.get(tm0.vid)
        tm1.count = 7
        tm1.save()

        tm0.reload()
        assert tm0.count == 7

class TestUpdateMethod(BaseCassEngTestCase):
    def test_success_case(self):
        """ Tests that the update method works as expected """
        tm = TestModel.create(count=8, text='123456789')
        tm2 = tm.update(count=9)

        tm3 = TestModel.get(tm.vid)
        assert tm2.count == 9
        assert tm3.count == 9

    def test_unknown_names_raise_exception(self):
        """ Tests that passing in names for columns that don't exist raises an exception """
        tm = TestModel.create(count=8, text='123456789')
        with self.assertRaises(TypeError):
            tm.update(jon='beard')


class TestVertexTraversal(BaseCassEngTestCase):

    def setUp(self):
        super(TestVertexTraversal, self).setUp()
        self.v1 = TestModel.create(count=1, text='Test1')
        self.v2 = TestModel.create(count=2, text='Test2')
        self.v3 = OtherTestModel.create(count=3, text='Test3')
        
    def test_outgoing_vertex_traversal(self):
        """Test that outgoing vertex traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = TestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v1.outV(TestEdge)
        assert len(results) == 2
        assert self.v2 in results
        assert self.v3 in results

        results = self.v1.outV(TestEdge, allowed_elements=[OtherTestModel])
        assert len(results) == 1
        assert self.v3 in results

    
    def test_incoming_vertex_traversal(self):
        """Test that incoming vertex traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = TestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v2.inV(TestEdge)
        assert len(results) == 1
        assert self.v1 in results

        results = self.v2.inV(TestEdge, allowed_elements=[OtherTestModel])
        assert len(results) == 0

    def test_outgoing_edge_traversals(self):
        """Test that outgoing edge traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = OtherTestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v2.outE()
        assert len(results) == 1
        assert e3 in results

        results = self.v2.outE(allowed_elements=[TestEdge])
        assert len(results) == 0

    def test_incoming_edge_traversals(self):
        """Test that incoming edge traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = OtherTestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v2.inE()
        assert len(results) == 1
        assert e1 in results

        results = self.v2.inE(allowed_elements=[OtherTestEdge])
        assert len(results) == 0
