from unittest import skip
from thunderdome import connection 
from thunderdome.tests.base import BaseCassEngTestCase

from thunderdome.tests.models import TestModel, TestEdge

from thunderdome import gremlin
from thunderdome import models
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

class DeserializationTestModel(Vertex):
    count = columns.Integer()
    text  = columns.Text()

    gremlin_path = 'deserialize.groovy'

    get_map = gremlin.GremlinValue()
    get_list = gremlin.GremlinMethod()

class TestNestedDeserialization(BaseCassEngTestCase):
    """
    Tests that vertices are properly deserialized when nested in map and list data structures
    """

    def test_map_deserialization(self):
        """
        Tests that elements nested in maps are properly deserialized
        """
        
        original = DeserializationTestModel.create(count=5, text='happy')
        nested = original.get_map()

        assert isinstance(nested, dict)
        assert nested['vertex'] == original
        assert nested['number'] == 5

    def test_list_deserialization(self):
        """
        Tests that elements nested in lists are properly deserialized
        """
        
        original = DeserializationTestModel.create(count=5, text='happy')
        nested = original.get_list()

        assert isinstance(nested, list)
        assert nested[0] == None
        assert nested[1] == 0
        assert nested[2] == 1

        assert isinstance(nested[3], list)
        assert nested[3][0] == 2
        assert nested[3][1] == original
        assert nested[3][2] == 3

        assert nested[4] == 5

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

class TestIndexCreation(BaseCassEngTestCase):
    """
    Tests that automatic index creation works as expected
    """
    def setUp(self):
        super(TestIndexCreation, self).setUp()
        self.old_create_index = connection.create_key_index
        self.index_calls = []
        def new_create_index(name):
            #fire blanks
            self.index_calls.append(name)
            #return self.old_create_index(name)
        connection.create_key_index = new_create_index

        self.old_vertex_types = models.vertex_types
        models.vertex_types = {}

        self.old_index_setting = connection._index_all_fields

    def tearDown(self):
        super(TestIndexCreation, self).tearDown()
        models.vertex_types = self.old_vertex_types
        connection._index_all_fields = self.old_index_setting
        connection.create_key_index = self.old_create_index 

    def test_create_index_is_called(self):
        """
        Tests that create_key_index is called when defining indexed columns
        """
        assert len(self.index_calls) == 0

        connection._index_all_fields = False
        
        class TestIndexCreationCallTestVertex(Vertex):
            col1 = columns.Text(index=True)
            col2 = columns.Text(index=True, db_field='____column')
            col3 = columns.Text(db_field='____column3')

        assert len(self.index_calls) == 2
        assert 'vid' not in self.index_calls
        assert 'col1' in self.index_calls
        assert '____column' in self.index_calls
        assert '____column3' not in self.index_calls

        connection._index_all_fields = True
        self.index_calls = []

        class TestIndexCreationCallTestVertex2(Vertex):
            col1 = columns.Text()
            col2 = columns.Text(db_field='____column')

        assert len(self.index_calls) == 3
        assert 'vid' in self.index_calls
        assert 'col1' in self.index_calls
        assert '____column' in self.index_calls
