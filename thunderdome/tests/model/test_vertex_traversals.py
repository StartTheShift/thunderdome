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

from thunderdome import connection 
from thunderdome.tests.base import BaseCassEngTestCase

from thunderdome.models import Vertex, Edge
from thunderdome import columns


# Vertices
class Person(Vertex):
    name = columns.Text()
    age  = columns.Integer()


class Course(Vertex):
    name = columns.Text()
    credits = columns.Decimal()

# Edges
class EnrolledIn(Edge):
    date_enrolled = columns.DateTime()

    
class TaughtBy(Edge):
    overall_mood = columns.Text(default='Grumpy')
    

class TestVertexTraversals(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        cls.jon = Person.create(name='Jon', age=143)
        cls.eric = Person.create(name='Eric', age=25)
        cls.blake = Person.create(name='Blake', age=14)

        cls.physics = Course.create(name='Physics 264', credits=1.0)
        cls.beekeeping = Course.create(name='Beekeeping', credits=15.0)
        cls.theoretics = Course.create(name='Theoretical Theoretics', credits=-3.5)

        cls.eric_in_physics = EnrolledIn.create(cls.eric, cls.physics, date_enrolled=datetime.now())
        cls.jon_in_beekeeping = EnrolledIn.create(cls.jon, cls.beekeeping, date_enrolled=datetime.now())
        cls.blake_in_theoretics = EnrolledIn.create(cls.blake, cls.theoretics, date_enrolled=datetime.now())

        cls.blake_beekeeping = TaughtBy.create(cls.beekeeping, cls.blake, overall_mood='Pedantic')
        cls.jon_physics = TaughtBy.create(cls.physics, cls.jon, overall_mood='Creepy')
        cls.eric_theoretics = TaughtBy.create(cls.theoretics, cls.eric, overall_mood='Obtuse')
        
    def test_inV_works(self):
        """Test that inV traversals work as expected"""
        results = self.jon.inV()
        assert len(results) == 1
        assert self.physics in results

        results = self.physics.inV()
        assert len(results) == 1
        assert self.eric in results

        results = self.eric.inV()
        assert len(results) == 1
        assert self.theoretics in results

        results = self.theoretics.inV()
        assert len(results) == 1
        assert self.blake in results

        results = self.beekeeping.inV()
        assert len(results) == 1
        assert self.jon in results

        results = self.blake.inV()
        assert len(results) == 1
        assert self.beekeeping in results

    def test_inE_traversals(self):
        """Test that inE traversals work as expected"""
        results = self.jon.inE()
        assert len(results) == 1
        assert self.jon_physics in results

    def test_outV_traversals(self):
        """Test that outV traversals work as expected"""
        results = self.eric.outV()
        assert len(results) == 1
        assert self.physics in results

    def test_outE_traverals(self):
        """Test that outE traversals work as expected"""
        results = self.blake.outE()
        assert len(results) == 1
        assert self.blake_in_theoretics in results

    def test_bothE_traversals(self):
        """Test that bothE traversals works"""
        results = self.jon.bothE()
        assert len(results) == 2
        assert self.jon_physics in results
        assert self.jon_in_beekeeping in results

    def test_bothV_traversals(self):
        """Test that bothV traversals work"""
        results = self.blake.bothV()
        assert len(results) == 2
        assert self.beekeeping in results
