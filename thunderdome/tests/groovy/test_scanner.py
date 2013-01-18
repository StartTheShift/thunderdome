import os

from unittest import TestCase
from thunderdome.gremlin import parse

class GroovyScannerTest(TestCase):
    """
    Test Groovy language scanner
    """
    
    def test_parsing_complicated_function(self):
        groovy_file = os.path.join(os.path.dirname(__file__), 'test.groovy')
        result = parse(groovy_file)
        assert len(result[6].body.split('\n')) == 8

        result_map = {x.name: x for x in result}
        assert 'get_self' in result_map
        assert 'return_value' in result_map
        assert 'long_func' in result_map
