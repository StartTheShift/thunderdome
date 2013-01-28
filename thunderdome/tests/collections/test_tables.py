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

from thunderdome.containers import Table

from unittest import TestCase

class Person(object):
    def __init__(self, name):
        self.name = name

class SomeEdge(object):
    def __init__(self, nickname):
        self.nickname = nickname
    

class TableTest(TestCase):
    def setUp(self):
        self.data = [{'v':Person('jon'), 'e':SomeEdge('rustyrazorblade')},
                     {'v':Person('eric'), 'e':SomeEdge('enasty')},
                     {'v':Person('blake'), 'e':SomeEdge('bmoney')}]
        self.t = Table(self.data)
    
    def test_length(self):
        assert len(self.t) == 3
    
    def test_iteration(self):
        i = 0
        for r in self.t:
            i += 1
            assert r.v.name is not None
        assert i == 3
        
    def test_access_element(self):
        assert self.t[0].v.name == 'jon'
        assert self.t[0].e.nickname == 'rustyrazorblade'
        
        assert self.t[1].v.name == 'eric', self.t[1].v.name
        assert self.t[2].e.nickname == 'bmoney'
        
        
            
