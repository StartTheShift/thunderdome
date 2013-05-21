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
from decimal import Decimal as D

from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.properties import Column
from thunderdome.properties import Text
from thunderdome.properties import Integer
from thunderdome.properties import DateTime
from thunderdome.properties import Dictionary
from thunderdome.properties import UUID
from thunderdome.properties import Boolean
from thunderdome.properties import Float
from thunderdome.properties import List
from thunderdome.properties import Decimal

from thunderdome.models import Vertex

from thunderdome.exceptions import ValidationError

class DatetimeTest(Vertex):
    test_id = Integer(primary_key=True)
    created_at = DateTime(required=False)
    

class DatetimeCoercionTest(Vertex):
    test_id = Integer(primary_key=True)
    created_at = DateTime(required=False, strict=False)

    
class TestDatetime(BaseThunderdomeTestCase):

    def test_datetime_io(self):
        now = datetime.now()
        dt = DatetimeTest.create(test_id=0, created_at=now)
        dt2 = DatetimeTest.get(dt.vid)
        assert dt2.created_at.timetuple()[:6] == now.timetuple()[:6]

    def test_none_handling(self):
        """
        Tests the handling of NoneType
        :return:
        """
        dt = DatetimeTest.create(test_id=0, created_at=None)

    def test_coercion_of_floats(self):
        with self.assertRaises(ValidationError):
            dt = DatetimeTest.create(test_id=1)
            dt.created_at = 12309834.234
            dt.save()

        dt2 = DatetimeCoercionTest.create(test_id=2)
        dt2.created_at = 1362470400
        dt2.save()
        dt2.created_at = 1098234098.2098
        dt2.save()
        dt2.created_at = '120398231'
        dt2.save()
        dt2.created_at = '12039823.198'
        dt2.save()
        dt2.reload()
        assert isinstance(dt2.created_at, datetime)


class DecimalTest(Vertex):
    test_id = Integer(primary_key=True)
    dec_val = Decimal()
    
class TestDecimal(BaseThunderdomeTestCase):

    def test_datetime_io(self):
        dt = DecimalTest.create(test_id=0, dec_val=D('0.00'))
        dt2 = DecimalTest.get(dt.vid)
        assert dt2.dec_val == dt.dec_val

        dt = DecimalTest.create(test_id=0, dec_val=5)
        dt2 = DecimalTest.get(dt.vid)
        assert dt2.dec_val == D('5')

class TestText(BaseThunderdomeTestCase):

    def test_max_length_validation(self):
        """
        Tests that the max_length kwarg works
        """

class TestInteger(BaseThunderdomeTestCase):

    def test_non_integral_validation(self):
        """
        Tests that attempting to save non integral values raises a ValidationError
        """

class TestFloat(BaseThunderdomeTestCase):

    def test_non_numberic_validation(self):
        """
        Tests that attempting to save a non numeric value raises a ValidationError
        """

class DictionaryTestVertex(Vertex):
    test_id = Integer(primary_key=True)
    map_val = Dictionary()

class TestDictionary(BaseThunderdomeTestCase):

    def test_dictionary_io(self):
        """ Tests that dictionary objects are saved and loaded successfully """
        dict_val = {'blake':31, 'something_else':'that'}
        v1 = DictionaryTestVertex.create(test_id=5, map_val=dict_val)
        v2 = DictionaryTestVertex.get(v1.vid)

        assert v2.map_val == dict_val

    def test_validation(self):
        """ Tests that the Dictionary column validates values properly """

        with self.assertRaises(ValidationError):
            Dictionary().validate([1,2,3])

        with self.assertRaises(ValidationError):
            Dictionary().validate('stringy')

        with self.assertRaises(ValidationError):
            Dictionary().validate(1)

class ListTestVertex(Vertex):
    test_id = Integer(primary_key=True)
    list_val = List()

class TestList(BaseThunderdomeTestCase):

    def test_dictionary_io(self):
        """ Tests that dictionary objects are saved and loaded successfully """
        list_val = ['blake', 31, 'something_else', 'that']
        v1 = ListTestVertex.create(test_id=5, list_val=list_val)
        v2 = ListTestVertex.get(v1.vid)

        assert v2.list_val == list_val

    def test_validation(self):
        """ Tests that the Dictionary column validates values properly """

        with self.assertRaises(ValidationError):
            List().validate({'blake':31, 'something_else':'that'})

        with self.assertRaises(ValidationError):
            List().validate('stringy')

        with self.assertRaises(ValidationError):
            List().validate(1)














