'''
Created on Jan 18, 2013

@author: jonhaddad
'''

from thunderdome.containers import Table

'''
Created on Jan 18, 2013

@author: jonhaddad
'''
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
        
        
            