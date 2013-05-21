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
import uuid

from thunderdome.properties import *
from thunderdome.tests.base import BaseThunderdomeTestCase

class TestDefaultValue(BaseThunderdomeTestCase):
    """ Tests that setting default values works on all column types """

    def test_string_default(self):
        """ Tests string defaults work properly """
        default = 'BLAKE!'
        prop = String(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_integer_default(self):
        """ Tests integer defaults work properly """
        default = 5
        prop = Integer(default=5, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_datetime_default(self):
        """ Tests datetime defaults work properly """
        default = datetime.now()
        prop = DateTime(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_uuid_default(self):
        """ Tests uuid defaults work properly """
        default = uuid.uuid4()
        prop = UUID(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_boolean_default(self):
        """ Tests boolean defaults work properly """
        default = True
        prop = Boolean(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_double_default(self):
        """ Tests double defaults work properly """
        default = 7.0
        prop = Double(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_decimal_default(self):
        """ Tests decimal defaults work properly """
        default = D('2.00')
        prop = Decimal(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_dictionary_default(self):
        """ Tests dictionary defaults work properly """
        default = {1:2}
        prop = Dictionary(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))

    def test_list_default(self):
        """ Tests list defaults work properly """
        default = [1,2]
        prop = String(default=default, required=True)
        self.assertEqual(prop.to_database(None), prop.to_database(default))
