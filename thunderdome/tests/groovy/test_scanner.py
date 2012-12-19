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
        import ipdb; ipdb.set_trace()