from thunderdome.tests.base import BaseCassEngTestCase

from thunderdome.models import Vertex
from thunderdome import columns
from thunderdome import gremlin

class GroovyTestModel(Vertex):
    gremlin_path = 'test.groovy'
    
    text    = columns.Text()
    get_self = gremlin.GremlinMethod()
    cm_get_self = gremlin.GremlinMethod(method_name='get_self', classmethod=True)
    
class TestMethodLoading(BaseCassEngTestCase):
    
    def test_method_loads_and_works(self):
        v1 = GroovyTestModel.create(text='cross fingers')
        
        v2 = v1.get_self()
        assert v1.vid == v2[0].vid
        
        v3 = v1.cm_get_self(v1.eid)
        assert v1.vid == v3[0].vid
        

class TestMethodArgumentHandling(BaseCassEngTestCase):

    def test_proper_argument_handling(self):
        """
        Test that supplying too many or too few arguments raises a TypeError
        """

    def test_proper_kwargs_handling(self):
        """
        Tests that supplying a mix of args and kwargs works
        """
    


