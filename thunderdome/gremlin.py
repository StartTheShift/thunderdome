import inspect
import os.path
import time
import logging

from thunderdome.connection import execute_query
from thunderdome.exceptions import ThunderdomeException
from thunderdome.groovy import parse
from containers import Table

logger = logging.getLogger(__name__)

class ThunderdomeGremlinException(ThunderdomeException):pass

class BaseGremlinMethod(object):
    """ Maps a function in a groovy file to a method on a python class """
    
    def __init__(self, path=None, method_name=None, classmethod=False, property=False, defaults={}, transaction=True):
        """
        :param path: path to the source gremlin file, relative to the file the class is defined in
            absolute paths also work, defaults to gremlin.groovy if left blank
        :param method_name: the name of the function definition in the groovy file.
            defaults to the attribute name this is instantiated on
        :param classmethod: method will behave as a classmethod if this is True, defaults to False
        :param property: method will behave as a property if this is True, defaults to False
        :param defaults: default values for arguments
        :param transaction: defaults to True, closes any previous transactions before executing query
        """
        self.is_configured = False
        self.path = path
        self.method_name = method_name
        self.classmethod = classmethod
        self.property = property
        self.defaults =defaults
        self.transaction = transaction
        
        self.attr_name = None
        self.arg_list = []
        self.function_body = None
        self.function_def = None
        
    def configure_method(self, klass, attr_name, gremlin_path):
        """
        Configures the methods internals
        
        :param klass: the class object this function is being added onto
        :param attr_name: the attribute name this function is being added to the class as
        """
        self.attr_name = attr_name
        self.method_name = self.method_name or self.attr_name
        if not self.is_configured:
            self.path = self.path or gremlin_path or 'gremlin.groovy'
            if self.path.startswith('/'):
                path = self.path
            else:
                path = inspect.getfile(klass)
                path = os.path.split(path)[0]
                path += '/' + self.path
                
            #TODO: make this less naive
            gremlin_obj = None
            for grem_obj in parse(path):
                if grem_obj.name == self.method_name:
                    gremlin_obj = grem_obj
                    break
                
            if gremlin_obj is None:
                raise ThunderdomeGremlinException("The method'{}' wasnt found in {}".format(self.method_name, path))
            
            for arg in gremlin_obj.args:
                if arg in self.arg_list:
                    raise ThunderdomeGremlinException("'{}' defined more than once in gremlin method arguments".format(arg))
                self.arg_list.append(arg)
            
            self.function_body = gremlin_obj.body
            self.function_def = gremlin_obj.defn
            self.is_configured = True
        
    def __call__(self, instance, *args, **kwargs):
        args = list(args)
        if not self.classmethod:
            args = [instance.eid] + args
            
        params = self.defaults.copy()
        if len(args + kwargs.values()) > len(self.arg_list):
            raise TypeError('{}() takes {} args, {} given'.format(self.attr_name, len(self.arg_list), len(args)))

        #check for and calculate callable defaults
        for k,v in params.items():
            if callable(v):
                params[k] = v()

        arglist = self.arg_list[:]
        for arg in args:
            params[arglist.pop(0)] = arg
            
        for k,v in kwargs.items():
            if k not in arglist:
                an = self.attr_name
                if k in params:
                    raise TypeError(
                        "{}() got multiple values for keyword argument '{}'".format(an, k))
                else:
                    raise TypeError(
                        "{}() got an unexpected keyword argument '{}'".format(an, k))
            arglist.pop(arglist.index(k))
            params[k] = v
            

        params = self.transform_params_to_database(params)

        tmp = execute_query(self.function_body, params, transaction=self.transaction)
        return tmp
    
    def transform_params_to_database(self, params):
        #convert graph elements into their eids
        from datetime import datetime
        from decimal import Decimal as _Decimal
        from uuid import UUID as _UUID
        from thunderdome.models import BaseElement
        from thunderdome.columns import DateTime, Decimal, UUID
        
        if isinstance(params, dict):
            return {k:self.transform_params_to_database(v) for k,v in params.iteritems()}
        if isinstance(params, list):
            return [self.transform_params_to_database(x) for x in params]
        if isinstance(params, BaseElement):
            return params.eid
        if isinstance(params, datetime):
            return DateTime().to_database(params)
        if isinstance(params, _UUID):
            return UUID().to_database(params)
        if isinstance(params, _Decimal):
            return Decimal().to_database(params)
        return params
            
class GremlinMethod(BaseGremlinMethod):
    """ Gremlin method that returns a graph element """

    @staticmethod
    def _deserialize(obj):
        """ recursively deserializes elements returned from rexster """
        from thunderdome.models import Element

        if isinstance(obj, dict) and '_id' in obj and '_type' in obj:
            return Element.deserialize(obj)
        elif isinstance(obj, dict):
            return {k:GremlinMethod._deserialize(v) for k,v in obj.items()}
        elif isinstance(obj, list):
            return [GremlinMethod._deserialize(v) for v in obj]
        else:
            return obj

    def __call__(self, instance, *args, **kwargs):
        from thunderdome.models import Element
        results = super(GremlinMethod, self).__call__(instance, *args, **kwargs)
        return GremlinMethod._deserialize(results)

class GremlinValue(GremlinMethod):
    """ Gremlin Method that returns one value """
    def __call__(self, instance, *args, **kwargs):
        results = super(GremlinValue, self).__call__(instance, *args, **kwargs)

        if results is None: return
        if len(results) != 1:
            raise ThunderdomeGremlinException('GremlinValue requires a single value is returned ({} returned)'.format(len(results)))

        return results[0]

class GremlinTable(GremlinMethod):
    def __call__(self, instance, *args, **kwargs):
        results = super(GremlinTable, self).__call__(instance, *args, **kwargs)
        if results is None: return
        return Table(results)
