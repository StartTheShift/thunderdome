from thunderdome.connection import ThunderdomeQueryError
from thunderdome.tests.base import BaseThunderdomeTestCase
from thunderdome.models import Query, IN, OUT, Edge, Vertex, GREATER_THAN
from thunderdome import Integer, Double


class MockVertex(object):
    eid = 1

class MockVertex2(Vertex):
    age = Integer()

class MockEdge(Edge):
    age = Integer()
    fierceness = Double()


class SimpleQueryTest(BaseThunderdomeTestCase):
    def setUp(self):
        self.q = Query(MockVertex())

    def test_limit(self):
        result = self.q.limit(10)._get_partial()
        assert result == "g.v(eid).query().limit(limit)"

    def test_direction_in(self):
        result = self.q.direction(IN)._get_partial()
        assert result == "g.v(eid).query().direction(IN)"

    def test_direction_out(self):
        result = self.q.direction(OUT)._get_partial()
        assert result == "g.v(eid).query().direction(OUT)"

    def test_labels(self):
        result = self.q.labels('test')._get_partial()
        assert result == "g.v(eid).query().labels('test')"
        # ensure the original wasn't modified
        assert self.q._labels == []

    def test_2labels(self):
        result = self.q.labels('test', 'test2')._get_partial()
        assert result == "g.v(eid).query().labels('test', 'test2')"

    def test_object_label(self):
        result = self.q.labels(MockEdge)._get_partial()
        assert result == "g.v(eid).query().labels('mock_edge')", result

    # def test_has(self):
    #     result = self.q.has(MockEdge.age, 10)._get_parial()
    #     assert result == "g.v(eid).has('prop','val')"
    #
    # def test_has_double_casting(self):
    #     result = self.q.has(MockEdge.fierceness, 3.3)._get_parial()
    #     assert result == "g.v(eid).has('fierceness',3.3 as double)"

    def test_direction_except(self):
        with self.assertRaises(ThunderdomeQueryError):
            self.q.direction(OUT).direction(OUT)

    def test_has_double_casting(self):
        result = self.q.has('fierceness', 3.3)._get_partial()
        assert result == "g.v(eid).query().has('fierceness', v0 as double, Query.Compare.EQUAL)", result

    def test_has_int(self):
        result = self.q.has('age', 21, GREATER_THAN)._get_partial()
        assert result == "g.v(eid).query().has('age', v0, Query.Compare.GREATER_THAN)", result

    def test_intervals(self):
        result = self.q.interval('age', 10, 20)._get_partial()
        assert result == "g.v(eid).query().interval('age', v0, v1)", result

    def test_double_interval(self):
        result = self.q.interval('fierceness', 2.5, 5.2)._get_partial()
        assert result == "g.v(eid).query().interval('fierceness', v0 as double, v1 as double)", result

