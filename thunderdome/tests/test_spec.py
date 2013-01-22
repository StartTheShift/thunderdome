from thunderdome.tests.base import BaseCassEngTestCase
from thunderdome.spec import SpecParser


class SpecParserTest(BaseCassEngTestCase):
    """Test spec parsing from dictionary objects"""

    @classmethod
    def setUpClass(cls):
        cls.spec_parser = SpecParser()
        cls.property_spec = {
            'type': 'property',
            'name': 'updated_at',
            'data_type': 'Integer',
            'functional': True
        }
        cls.edge_spec = {
            'type': 'edge',
            'label': 'subscribed_to',
            'primary_key': 'updated_at'
        }
        
    def test_should_return_error_if_stmt_contains_no_type(self):
        """Should raise error if statement contains no type"""
        with self.assertRaises(TypeError):
            self.spec_parser.parse_statement({'name': 'todd'})

    def test_should_raise_error_if_type_is_invalid(self):
        """Should raise error if type is invalid"""
        with self.assertRaises(ValueError):
            self.spec_parser.parse_statement({'type': 'sugar'})

    def test_should_return_correct_gremlin_for_property(self):
        """Should construct the correct Gremlin code for a property"""
        expected = 'g.makeType().name("updated_at").dataType(Integer.class).functional().makePropertyKey()'
        prop = self.spec_parser.parse_property(self.property_spec)
        assert prop.gremlin == expected

        expected = 'g.makeType().name("updated_at").dataType(Integer.class).makePropertyKey()'
        self.property_spec['functional'] = False
        prop = self.spec_parser.parse_property(self.property_spec)
        assert prop.gremlin == expected

    def test_should_return_correct_gremlin_for_edge(self):
        """Should return correct gremlin for an edge"""
        expected = 'g.makeType().name("subscribed_to").primaryKey(updated_at).makeEdgeLabel()'
        edge = self.spec_parser.parse_edge(self.edge_spec)
        assert edge.gremlin == expected

        expected = 'g.makeType().name("subscribed_to").makeEdgeLabel()'
        del self.edge_spec['primary_key']
        edge = self.spec_parser.parse_edge(self.edge_spec)
        assert edge.gremlin == expected
