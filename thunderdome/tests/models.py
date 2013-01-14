from thunderdome.models import Vertex, Edge
from thunderdome import columns


class TestModel(Vertex):
    count   = columns.Integer()
    text    = columns.Text(required=False)

    
class TestEdge(Edge):
    numbers = columns.Integer()
