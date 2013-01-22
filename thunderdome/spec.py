import json


class Property(object):
    """Abstracts a property parsed from a spec file."""

    def __init__(self, name, data_type, functional=False):
        """
        Defines a property parsed from a spec file.

        :param name: The name of the property
        :type name: str
        :param data_type: The Java data type to be used for this property
        :type data_type: str
        :param functional: Indicates whether or not this is a functional property
        :type functional: boolean
        
        """
        self.name = name
        self.data_type = data_type
        self.functional = functional

    @property
    def gremlin(self):
        """
        Return the gremlin code for creating this property.

        :rtype: str
        
        """
        initial = 'g.makeType().name("{}").dataType({}.class).{}makePropertyKey()'
        func = ''
        if self.functional:
            func = 'functional().'
        return initial.format(self.name, self.data_type, func)


class Edge(object):
    """Abstracts an edge parsed from a spec file."""

    def __init__(self, label, primary_key=None):
        """
        Defines an edge parsed from a spec file.

        :param label: The label for this edge
        :type label: str
        :param primary_key: The primary key for this edge
        :type primary_key: thunderdome.spec.Property or None
        
        """
        self.label = label
        self.primary_key = primary_key

    @property
    def gremlin(self):
        """
        Return the gremlin code for creating this edge.

        :rtype: str
        
        """
        initial = 'g.makeType().name("{}").{}makeEdgeLabel()'
        primary_key = ''
        if self.primary_key:
            primary_key = "primaryKey({}).".format(self.primary_key)
        return initial.format(self.label, primary_key)
    

class SpecParser(object):
    """
    Parser for a spec file describing properties and primary keys for edges.
    This file is used to ensure duplicate primary keys are not created.

    File format:

    [
        {
            "type":"property",
            "name":"updated_at",
            "data_type":"Integer",
            "functional":true
        }
        {
            "type":"edge",
            "label":"subscribed_to",
            "primary_key":"updated_at"
        }
 
    ]

    """

    _specs = {}

    def __init__(self, filename=None):
        """
        Pass in the 
        
        :param filename: The path to the file to be parsed
        :type filename: str

        :rtype: dict
        
        """
        if filename:
            self._specs = json.dumps(filename)

    def parse(self):
        """
        Parse the internal spec and return a list of gremlin statements.

        :rtype: list
        
        """
        return []

    def parse_property(self, stmt):
        """
        Build object for a new property type.

        :param stmt: The statement to be parsed
        :type stmt: str

        :rtype: thunderdome.spec.Property

        """
        return Property(name=stmt['name'],
                        data_type=stmt['data_type'],
                        functional=stmt.get('functional', False))

    def parse_edge(self, stmt):
        """
        Build object for a new edge with a primary key.

        :param stmt: The statement to be parsed
        :type stmt: str

        :rtype: thunderdome.spec.Edge
        
        """
        return Edge(label=stmt['label'],
                    primary_key=stmt.get('primary_key'))

    def parse_statement(self, stmt):
        """
        Takes the given spec statement and converts it into an object.

        :param stmt: The statement
        :type stmt: dict

        :rtype: thunderdome.spec.Property or thunderdome.spec.Edge

        """
        if 'type' not in stmt:
            raise TypeError('Type field required')

        if stmt['type'] == 'property':
            return parse_property(stmt)
        elif stmt['type'] == 'edge':
            return parse_edge(stmt)
        else:
            raise ValueError('Invalid `type` value {}'.format(stmt['type']))
