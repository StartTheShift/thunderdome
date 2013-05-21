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

from datetime import datetime
from unittest import skip
from uuid import uuid4

from thunderdome.gremlin import ThunderdomeGremlinException
from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.models import Vertex
from thunderdome import properties
from thunderdome import gremlin

class GroovyTestModel(Vertex):
    text    = properties.Text()
    get_self = gremlin.GremlinMethod()
    cm_get_self = gremlin.GremlinMethod(method_name='get_self', classmethod=True)

    return_default = gremlin.GremlinValue(method_name='return_value', defaults={'val':lambda:5000})
    return_list = gremlin.GremlinValue(property=1)
    return_value = gremlin.GremlinValue()

    arg_test1 = gremlin.GremlinValue()
    arg_test2 = gremlin.GremlinValue()

class TestMethodLoading(BaseThunderdomeTestCase):
    
    def test_method_loads_and_works(self):
        v1 = GroovyTestModel.create(text='cross fingers')
        
        v2 = v1.get_self()
        assert v1.vid == v2[0].vid
        
        v3 = v1.cm_get_self(v1.eid)
        assert v1.vid == v3[0].vid
        

class TestMethodArgumentHandling(BaseThunderdomeTestCase):

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
        assert v1.return_value(now) == properties.DateTime().to_database(now)

        uu = uuid4()
        assert v1.return_value(uu) == properties.UUID().to_database(uu)

    def test_initial_arg_name_isnt_set(self):
        """ Tests that the name of the first argument in a instance method """
        v = GroovyTestModel.create(text='cross fingers')

        assert v == v.arg_test1()
        assert v == v.arg_test2()
