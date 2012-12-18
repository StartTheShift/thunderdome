from unittest import TestCase
from thunderdome import connection

from thunderdome.models import Vertex, Edge
from thunderdome import columns

class TestModel(Vertex):
    count   = columns.Integer()
    text    = columns.Text(required=False)
    
class TestEdge(Edge):
    numbers = columns.Integer()

class BaseCassEngTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseCassEngTestCase, cls).setUpClass()
        if not connection._hosts:
            connection.setup(['localhost'], 'grapheffect')

    def assertHasAttr(self, obj, attr):
        self.assertTrue(hasattr(obj, attr), 
                "{} doesn't have attribute: {}".format(obj, attr))

    def assertNotHasAttr(self, obj, attr):
        self.assertFalse(hasattr(obj, attr), 
                "{} shouldn't have the attribute: {}".format(obj, attr))
