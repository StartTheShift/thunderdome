import inspect
import os.path
import time
import logging

from thunderdome.connection import execute_query, ThunderdomeQueryError
from thunderdome.exceptions import ThunderdomeException
from thunderdome.groovy import parse
from containers import Table


logger = logging.getLogger(__name__)


class ThunderdomeGremlinException(ThunderdomeException):
    """
    Exception thrown when a Gremlin error is encountered
    """


class BaseGremlinMethod(object):
    """ Maps a function in a groovy file to a method on a python class """

    def __init__(self,
                 path=None,
                 method_name=None,
                 classmethod=False,
                 property=False,
                 defaults={},
                 transaction=True):
        """
        Initialize the gremlin method and define how it is attached to class.

        :param path: Path to the gremlin source (relative to file class is
        defined in). Absolute paths work as well. Defaults to gremlin.groovy.
        :type path: str
        :param method_name: The name of the function definition in the groovy file
        :type method_name: str
        :param classmethod: Method should behave as a classmethod if True
        :type classmethod: boolean
        :param property: Method should behave as a property
        :type property: boolean
        :param defaults: The default parameters to the function
        :type defaults: dict
        :param transaction: Close previous transaction before executing (True
        by default)
        :type transaction: boolean

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

        :param klass: The class object this function is being added to
        :type klass: object
        :param attr_name: The attribute name this function will be added as
        :type attr_name: str
        :param gremlin_path: The path to the gremlin file containing method
        :type gremlin_path: str

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
                raise ThunderdomeGremlinException("The method '{}' wasnt found in {}".format(self.method_name, path))

            for arg in gremlin_obj.args:
                if arg in self.arg_list:
                    raise ThunderdomeGremlinException("'{}' defined more than once in gremlin method arguments".format(arg))
                self.arg_list.append(arg)

            self.function_body = gremlin_obj.body
            self.function_def = gremlin_obj.defn
            self.is_configured = True

    def __call__(self, instance, *args, **kwargs):
        """
        Intercept attempts to call the GremlinMethod attribute and perform a
        gremlin query returning the results.

        :param instance: The class instance the method was called on
        :type instance: object

        """
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

        try:
            tmp = execute_query(self.function_body, params, transaction=self.transaction)
        except ThunderdomeQueryError as tqe:
            import pprint
            msg  = "Error while executing Gremlin method\n\n"
            msg += "[Method]\n{}\n\n".format(self.method_name)
            msg += "[Params]\n{}\n\n".format(pprint.pformat(params))
            msg += "[Function Body]\n{}\n".format(self.function_body)
            msg += "\n[Error]\n{}\n".format(tqe)
            raise ThunderdomeGremlinException(msg)
        return tmp

    def transform_params_to_database(self, params):
        """
        Takes a dictionary of parameters and recursively translates them into
        parameters appropriate for sending over Rexster.

        :param params: The parameters to be sent to the function
        :type params: dict

        """

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
    """Gremlin method that returns a graph element"""

    @staticmethod
    def _deserialize(obj):
        """
        Recursively deserializes elements returned from rexster

        :param obj: The raw result returned from rexster
        :type obj: object

        """
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
        results = super(GremlinMethod, self).__call__(instance, *args, **kwargs)
        return GremlinMethod._deserialize(results)


class GremlinValue(GremlinMethod):
    """Gremlin Method that returns one value"""

    def __call__(self, instance, *args, **kwargs):
        results = super(GremlinValue, self).__call__(instance, *args, **kwargs)

        if results is None:
            return
        if len(results) != 1:
            raise ThunderdomeGremlinException('GremlinValue requires a single value is returned ({} returned)'.format(len(results)))

        return results[0]


class GremlinTable(GremlinMethod):
    """Gremlin method that returns a table as its result"""

    def __call__(self, instance, *args, **kwargs):
        results = super(GremlinTable, self).__call__(instance, *args, **kwargs)
        if results is None:
            return
        return Table(results)
