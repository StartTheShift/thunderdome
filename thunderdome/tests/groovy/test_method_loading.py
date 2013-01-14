from datetime import datetime
from unittest import skip
from uuid import uuid4

from thunderdome.gremlin import ThunderdomeGremlinException
from thunderdome.tests.base import BaseCassEngTestCase

from thunderdome.models import Vertex
from thunderdome import columns
from thunderdome import gremlin

class GroovyTestModel(Vertex):
    gremlin_path = 'test.groovy'
    
    text    = columns.Text()
    get_self = gremlin.GremlinMethod()
    cm_get_self = gremlin.GremlinMethod(method_name='get_self', classmethod=True)

    return_default = gremlin.GremlinValue(method_name='return_value', defaults={'val':lambda:5000})
    return_list = gremlin.GremlinValue(property=1)
    return_value = gremlin.GremlinValue()

class TestMethodLoading(BaseCassEngTestCase):
    
    def test_method_loads_and_works(self):
        v1 = GroovyTestModel.create(text='cross fingers')
        
        v2 = v1.get_self()
        assert v1.vid == v2[0].vid
        
        v3 = v1.cm_get_self(v1.eid)
        assert v1.vid == v3[0].vid
        

class TestMethodArgumentHandling(BaseCassEngTestCase):

    def test_callable_defaults(self):
        """
        Tests that callable default arguments are called
        """
        v1 = GroovyTestModel.create(text='cross fingers')
        assert v1.return_default() == 5000

    def test_gremlin_value_enforces_single_object_returned(self):
        """
        Tests that a GremlinValue instance raises an error if more than one object is returned
        """
        v1 = GroovyTestModel.create(text='cross fingers')
        with self.assertRaises(ThunderdomeGremlinException):
            v1.return_list

    def test_type_conversion(self):
        """ Tests that the gremlin method converts certain python objects to their gremlin equivalents """
        v1 = GroovyTestModel.create(text='cross fingers')

        now = datetime.now()
        assert v1.return_value(now) == columns.DateTime().to_database(now)

        uu = uuid4()
        assert v1.return_value(uu) == columns.UUID().to_database(uu)
