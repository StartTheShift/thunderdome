# -*- coding: utf-8 -*-
from unittest import skip
from thunderdome import connection
from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.tests.models import TestModel, TestEdge

from thunderdome import gremlin
from thunderdome import models
from thunderdome.models import Edge, Vertex
from thunderdome import properties

class DBFieldVertex(Vertex):
    text    = properties.Text(db_field='vertex_text')

class DBFieldEdge(Edge):
    text    = properties.Text(db_field='edge_text')

class TestDbField(BaseThunderdomeTestCase):

    def test_db_field_io(self):
        v1 = DBFieldVertex.create(text='vertex1')
        v2 = DBFieldVertex.create(text='vertex2')
        e1 = DBFieldEdge.create(v1, v2, text='edge1')

        v1_raw = connection.execute_query('g.v(eid)', params={'eid':v1.eid})
        assert v1.text == v1_raw[0]['vertex_text']

        v2_raw = connection.execute_query('g.v(eid)', params={'eid':v2.eid})
        assert v2.text == v2_raw[0]['vertex_text']

        e1_raw = connection.execute_query('g.e(eid)', params={'eid':e1.eid})
        assert e1.text == e1_raw[0]['edge_text']

