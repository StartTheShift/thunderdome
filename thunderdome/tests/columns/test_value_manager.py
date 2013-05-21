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

from datetime import datetime, timedelta

from thunderdome.properties import *
from thunderdome.tests.base import BaseThunderdomeTestCase


class TestChangedProperty(BaseThunderdomeTestCase):
    """
    Tests that the `changed` property works as intended
    """

    def test_string_update(self):
        """ Tests changes on string types """
        vm = String.value_manager(None, None, 'str')
        assert not vm.changed
        vm.value = 'unicode'
        assert vm.changed

    def test_string_inplace_update(self):
        """ Tests changes on string types """
        vm = String.value_manager(None, None, 'str')
        assert not vm.changed
        vm.value += 's'
        assert vm.changed

    def test_integer_update(self):
        """ Tests changes on string types """
        vm = Integer.value_manager(None, None, 5)
        assert not vm.changed
        vm.value = 4
        assert vm.changed

    def test_integer_inplace_update(self):
        """ Tests changes on string types """
        vm = Integer.value_manager(None, None, 5)
        assert not vm.changed
        vm.value += 1
        assert vm.changed

    def test_datetime_update(self):
        """ Tests changes on string types """
        now = datetime.now()
        vm = DateTime.value_manager(None, None, now)
        assert not vm.changed
        vm.value = now + timedelta(days=1)
        assert vm.changed

    def test_decimal_update(self):
        """ Tests changes on string types """
        vm = Decimal.value_manager(None, None, D('5.00'))
        assert not vm.changed
        vm.value = D('4.00')
        assert vm.changed

    def test_decimal_inplace_update(self):
        """ Tests changes on string types """
        vm = Decimal.value_manager(None, None, D('5.00'))
        assert not vm.changed
        vm.value += D('1.00')
        assert vm.changed

    def test_dictionary_update(self):
        """ Tests changes on string types """
        vm = Dictionary.value_manager(None, None, {1:2, 3:4})
        assert not vm.changed
        vm.value = {4:5}
        assert vm.changed

    def test_dictionary_inplace_update(self):
        """ Tests changes on string types """
        vm = Dictionary.value_manager(None, None, {1:2, 3:4})
        assert not vm.changed
        vm.value[4] = 5
        assert vm.changed

    def test_list_update(self):
        """ Tests changes on string types """
        vm = List.value_manager(None, None, [1,2,3])
        assert not vm.changed
        vm.value = [4,5,6]
        assert vm.changed

    def test_list_inplace_update(self):
        """ Tests changes on string types """
        vm = List.value_manager(None, None, [1,2,3])
        assert not vm.changed
        vm.value.append(4)
        assert vm.changed

