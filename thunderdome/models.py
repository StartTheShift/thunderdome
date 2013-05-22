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

from collections import OrderedDict
import inspect
import re
from uuid import UUID
import warnings

from thunderdome import properties
from thunderdome.connection import execute_query, create_key_index, ThunderdomeQueryError
from thunderdome.exceptions import ModelException, ValidationError, DoesNotExist, MultipleObjectsReturned, ThunderdomeException, WrongElementType
from thunderdome.gremlin import BaseGremlinMethod, GremlinMethod


#dict of node and edge types for rehydrating results
vertex_types = {}
edge_types = {}

# in blueprints this is part of the Query.compare
# see http://www.tinkerpop.com/docs/javadocs/blueprints/2.2.0/
EQUAL = "EQUAL"
GREATER_THAN = "GREATER_THAN"
GREATER_THAN_EQUAL = "GREATER_THAN_EQUAL"
LESS_THAN = "LESS_THAN"
LESS_THAN_EQUAL = "LESS_THAN_EQUAL"
NOT_EQUAL = "NOT_EQUAL"

# direction
OUT = "OUT"
IN = "IN"
BOTH = "BOTH"


class ElementDefinitionException(ModelException):
    """
    Error in element definition
    """

    
class SaveStrategyException(ModelException):
    """
    Violation of save strategy
    """


class BaseElement(object):
    """
    The base model class, don't inherit from this, inherit from Model, defined
    below
    """

    # When true this will prepend the module name to the type name of the class
    __use_module_name__ = False
    __default_save_strategy__ = properties.SAVE_ALWAYS
    
    class DoesNotExist(DoesNotExist):
        """
        Object not found in database
        """

    class MultipleObjectsReturned(MultipleObjectsReturned):
        """
        Multiple objects returned on unique key lookup
        """
        
    class WrongElementType(WrongElementType):
        """
        Unique lookup with key corresponding to vertex of different type
        """

    def __init__(self, **values):
        """
        Initialize the element with the given properties.

        :param values: The properties for this element
        :type values: dict
        
        """
        self.eid = values.get('_id')
        self._values = {}
        for name, column in self._columns.items():
            value = values.get(name, None)
            if value is not None:
                value = column.to_python(value)
            value_mngr = column.value_manager(self, column, value)
            self._values[name] = value_mngr

    def __eq__(self, other):
        """
        Check for equality between two elements.

        :param other: Element to be compared to
        :type other: BaseElement
        :rtype: boolean
        
        """
        if not isinstance(other, BaseElement): return False
        return self.as_dict() == other.as_dict() and self.eid == other.eid

    def __ne__(self, other):
        """
        Check for inequality between two elements.

        :param other: Element to be compared to
        :type other: BaseElement
        :rtype: boolean
        
        """
        return not self.__eq__(other)

    @classmethod
    def _type_name(cls, manual_name):
        """
        Returns the element name if it has been defined, otherwise it creates
        it from the module and class name.

        :param manual_name: Name to override the default type name
        :type manual_name: str
        :rtype: str
        
        """
        cf_name = ''
        if manual_name:
            cf_name = manual_name.lower()
        else:
            camelcase = re.compile(r'([a-z])([A-Z])')
            ccase = lambda s: camelcase.sub(lambda v: '{}_{}'.format(v.group(1), v.group(2).lower()), s)
    
            cf_name += ccase(cls.__name__)
            cf_name = cf_name.lower()
        if cls.__use_module_name__:
            cf_name = cls.__module__ + '_{}'.format(cf_name)
        return cf_name

    def validate_field(self, field_name, val):
        """
        Perform the validations associated with the field with the given name on
        the value passed.

        :param field_name: The name of column whose validations will be run
        :type field_name: str
        :param val: The value to be validated
        :type val: mixed
        
        """
        return self._columns[field_name].validate(val)

    def validate(self):
        """Cleans and validates the field values"""
        for name in self._columns.keys():
            func_name = 'validate_{}'.format(name)
            val = getattr(self, name)
            if hasattr(self, func_name):
                val = getattr(self, func_name)(val)
            else:
                val = self.validate_field(name, val)
            setattr(self, name, val)

    def as_dict(self):
        """
        Returns a map of column names to cleaned values

        :rtype: dict
        
        """
        values = {}
        for name, col in self._columns.items():
            values[name] = col.to_database(getattr(self, name, None))
        return values

    def as_save_params(self):
        """
        Returns a map of column names to cleaned values containing only the
        columns which should be persisted on save.

        :rtype: dict
        
        """
        values = {}
        was_saved = self.eid is not None
        for name, col in self._columns.items():
            # Determine the save strategy for this column
            should_save = True

            col_strategy = self.__default_save_strategy__
            if col.has_save_strategy:
                col_strategy = col.get_save_strategy()

            # Enforce the save strategy
            if col_strategy == properties.SAVE_ONCE:
                if was_saved:
                    if self._values[name].changed:
                        raise SaveStrategyException("Attempt to change column '{}' with save strategy SAVE_ONCE".format(name))
                    else:
                        should_save = False
            elif col_strategy == properties.SAVE_ONCHANGE:
                if was_saved and not self._values[name].changed:
                    should_save = False
            
            if should_save:
                values[col.db_field or name] = col.to_database(getattr(self, name, None))
                
        return values

    @classmethod
    def translate_db_fields(cls, data):
        """
        Translates field names from the database into field names used in our model

        this is for cases where we're saving a field under a different name than it's model property

        :param cls:
        :param data:
        :return:
        """
        dst_data = data.copy()
        for name, col in cls._columns.items():
            key = col.db_field or name
            if key in dst_data:
                dst_data[name] = dst_data.pop(key)

        return dst_data

    @classmethod
    def create(cls, *args, **kwargs):
        """Create a new element with the given information."""
        return cls(*args, **kwargs).save()
        
    def pre_save(self):
        """Pre-save hook which is run before saving an element"""
        self.validate()
        
    def save(self):
        """
        Base class save method. Performs basic validation and error handling.
        """
        if self.__abstract__:
            raise ThunderdomeException('cant save abstract elements')
        self.pre_save()
        return self

    def pre_update(self, **values):
        """ Override this to perform pre-update validation """
        pass

    def update(self, **values):
        """
        performs an update of this element with the given values and returns the
        saved object
        """
        if self.__abstract__:
            raise ThunderdomeException('cant update abstract elements')
        self.pre_update(**values)
        for key in values.keys():
            if key not in self._columns:
                raise TypeError("unrecognized attribute name: '{}'".format(key))

        for k,v in values.items():
            setattr(self, k, v)

        return self.save()

    def _reload_values(self):
        """
        Base method for reloading an element from the database.
        """
        raise NotImplementedError

    def reload(self):
        """
        Reload the given element from the database.
        """
        values = self._reload_values()
        for name, column in self._columns.items():
            value = values.get(column.db_field_name, None)
            if value is not None: value = column.to_python(value)
            setattr(self, name, value)
        return self

    
class ElementMetaClass(type):
    """Metaclass for all graph elements"""
    
    def __new__(cls, name, bases, attrs):
        """
        """
        #move column definitions into columns dict
        #and set default column names
        column_dict = OrderedDict()
        
        #get inherited properties
        for base in bases:
            for k,v in getattr(base, '_columns', {}).items():
                column_dict.setdefault(k,v)

        def _transform_column(col_name, col_obj):
            column_dict[col_name] = col_obj
            col_obj.set_column_name(col_name)
            #set properties
            _get = lambda self: self._values[col_name].getval()
            _set = lambda self, val: self._values[col_name].setval(val)
            _del = lambda self: self._values[col_name].delval()
            if col_obj.can_delete:
                attrs[col_name] = property(_get, _set, _del)
            else:
                attrs[col_name] = property(_get, _set)

        column_definitions = [(k,v) for k,v in attrs.items() if isinstance(v, properties.Column)]
        column_definitions = sorted(column_definitions, lambda x,y: cmp(x[1].position, y[1].position))
        
        #TODO: check that the defined columns don't conflict with any of the
        #Model API's existing attributes/methods transform column definitions
        for k,v in column_definitions:
            _transform_column(k,v)
            
        #check for duplicate column names
        col_names = set()
        for v in column_dict.values():
            if v.db_field_name in col_names:
                raise ModelException("{} defines the column {} more than once".format(name, v.db_field_name))
            col_names.add(v.db_field_name)

        #create db_name -> model name map for loading
        db_map = {}
        for field_name, col in column_dict.items():
            db_map[col.db_field_name] = field_name

        #add management members to the class
        attrs['_columns'] = column_dict
        attrs['_db_map'] = db_map
        
        #auto link gremlin methods
        gremlin_methods = {}
        
        #get inherited gremlin methods
        for base in bases:
            for k,v in getattr(base, '_gremlin_methods', {}).items():
                gremlin_methods.setdefault(k, v)

        #short circuit __abstract__ inheritance
        attrs['__abstract__'] = attrs.get('__abstract__', False)
                
        #short circuit path inheritance
        gremlin_path = attrs.get('gremlin_path')
        attrs['gremlin_path'] = gremlin_path

        def wrap_method(method):
            def method_wrapper(self, *args, **kwargs):
                return method(self, *args, **kwargs)
            return method_wrapper
        
        for k,v in attrs.items():
            if isinstance(v, BaseGremlinMethod):
                gremlin_methods[k] = v
                method = wrap_method(v)
                attrs[k] = method
                if v.classmethod: attrs[k] = classmethod(method)
                if v.property: attrs[k] = property(method)

        attrs['_gremlin_methods'] = gremlin_methods

        #create the class and add a QuerySet to it
        klass = super(ElementMetaClass, cls).__new__(cls, name, bases, attrs)
        
        #configure the gremlin methods
        for name, method in gremlin_methods.items():
            method.configure_method(klass, name, gremlin_path)
            
        return klass


class Element(BaseElement):
    __metaclass__ = ElementMetaClass
    
    @classmethod
    def deserialize(cls, data):
        """
        Deserializes rexster json into vertex or edge objects
        """
        dtype = data.get('_type')
        if dtype == 'vertex':
            vertex_type = data['element_type']
            if vertex_type not in vertex_types:
                raise ElementDefinitionException('Vertex "{}" not defined'.format(vertex_type))
            translated_data = vertex_types[vertex_type].translate_db_fields(data)
            return vertex_types[vertex_type](**translated_data)
        elif dtype == 'edge':
            edge_type = data['_label']
            if edge_type not in edge_types:
                raise ElementDefinitionException('Edge "{}" not defined'.format(edge_type))
            translated_data = edge_types[edge_type].translate_db_fields(data)
            return edge_types[edge_type](data['_outV'], data['_inV'], **translated_data)
        else:
            raise TypeError("Can't deserialize '{}'".format(dtype))
    
    
class VertexMetaClass(ElementMetaClass):
    """Metaclass for vertices."""
    
    def __new__(cls, name, bases, attrs):

        #short circuit element_type inheritance
        attrs['element_type'] = attrs.pop('element_type', None)

        klass = super(VertexMetaClass, cls).__new__(cls, name, bases, attrs)

        if not klass.__abstract__:
            element_type = klass.get_element_type()
            if element_type in vertex_types and str(vertex_types[element_type]) != str(klass):
                raise ElementDefinitionException('{} is already registered as a vertex'.format(element_type))
            vertex_types[element_type] = klass

            #index requested indexed columns
            klass._create_indices()

        return klass

    
class Vertex(Element):
    """
    The Vertex model base class. All vertexes have a vid defined on them, the
    element type is autogenerated from the subclass name, but can optionally be
    set manually
    """
    __metaclass__ = VertexMetaClass
    __abstract__ = True

    gremlin_path = 'vertex.groovy'

    _save_vertex = GremlinMethod()
    _traversal = GremlinMethod()
    _delete_related = GremlinMethod()

    #vertex id
    vid = properties.UUID(save_strategy=properties.SAVE_ONCE)
    
    element_type = None

    @classmethod
    def _create_indices(cls):
        """
        Creates this model's indices. This will be skipped if connection.setup
        hasn't been called, but connection.setup calls this method on existing
        vertices
        """
        from thunderdome.connection import _hosts, _index_all_fields, create_key_index
        
        if not _hosts: return
        for column in cls._columns.values():
            if column.index or _index_all_fields:
                create_key_index(column.db_field_name)
    
    @classmethod
    def get_element_type(cls):
        """
        Returns the element type for this vertex.

        :rtype: str
        
        """
        return cls._type_name(cls.element_type)
    
    @classmethod
    def all(cls, vids, as_dict=False):
        """
        Load all vertices with the given vids from the graph. By default this
        will return a list of vertices but if as_dict is True then it will
        return a dictionary containing vids as keys and vertices found as
        values.

        :param vids: A list of thunderdome UUIDS (vids)
        :type vids: list
        :param as_dict: Toggle whether to return a dictionary or list
        :type as_dict: boolean
        :rtype: dict or list
        
        """
        if not isinstance(vids, (list, tuple)):
            raise ThunderdomeQueryError("vids must be of type list or tuple")
        
        strvids = [str(v) for v in vids]
        qs = ['vids.collect{g.V("vid", it).toList()[0]}']
        
        results = execute_query('\n'.join(qs), {'vids':strvids})
        results = filter(None, results)
        
        if len(results) != len(vids):
            raise ThunderdomeQueryError("the number of results don't match the number of vids requested")
        
        objects = []
        for r in results:
            try:
                objects += [Element.deserialize(r)]
            except KeyError:
                raise ThunderdomeQueryError('Vertex type "{}" is unknown'.format())
            
        if as_dict:
            return {v.vid:v for v in objects}
        
        return objects

    def _reload_values(self):
        """
        Method for reloading the current vertex by reading its current values
        from the database.
        """
        results = execute_query('g.v(eid)', {'eid':self.eid})[0]
        del results['_id']
        del results['_type']
        return results

    @classmethod
    def get(cls, vid):
        """
        Look up vertex by thunderdome assigned UUID. Raises a DoesNotExist
        exception if a vertex with the given vid was not found. Raises a
        MultipleObjectsReturned exception if the vid corresponds to more than
        one vertex in the graph.

        :param vid: The thunderdome assigned UUID
        :type vid: str
        :rtype: thunderdome.models.Vertex
        
        """
        try:
            results = cls.all([vid])
            if len(results) >1:
                raise cls.MultipleObjectsReturned

            result = results[0]
            if not isinstance(result, cls):
                raise WrongElementType(
                    '{} is not an instance or subclass of {}'.format(result.__class__.__name__, cls.__name__)
                )
            return result
        except ThunderdomeQueryError:
            raise cls.DoesNotExist
    
    @classmethod
    def get_by_eid(cls, eid):
        """
        Look update a vertex by its Titan-specific id (eid). Raises a
        DoesNotExist exception if a vertex with the given eid was not found.

        :param eid: The numeric Titan-specific id
        :type eid: int
        :rtype: thunderdome.models.Vertex
        
        """
        results = execute_query('g.v(eid)', {'eid':eid})
        if not results:
            raise cls.DoesNotExist
        return Element.deserialize(results[0])
    
    def save(self, *args, **kwargs):
        """
        Save the current vertex using the configured save strategy, the default
        save strategy is to re-save all fields every time the object is saved.
        """
        super(Vertex, self).save(*args, **kwargs)
        params = self.as_save_params()
        params['element_type'] = self.get_element_type()
        result = self._save_vertex(params)[0]
        self.eid = result.eid
        for k,v in self._values.items():
            v.previous_value = result._values[k].previous_value
        return result
    
    def delete(self):
        """
        Delete the current vertex from the graph.
        """
        if self.__abstract__:
            raise ThunderdomeException('cant delete abstract elements')
        if self.eid is None:
            return self
        query = """
        g.removeVertex(g.v(eid))
        g.stopTransaction(SUCCESS)
        """
        results = execute_query(query, {'eid': self.eid})
        
    def _simple_traversal(self,
                          operation,
                          labels,
                          limit=None,
                          offset=None,
                          types=None):
        """
        Perform simple graph database traversals with ubiquitous pagination.

        :param operation: The operation to be performed
        :type operation: str
        :param labels: The edge labels to be used
        :type labels: list of Edges or strings
        :param start: The starting offset
        :type start: int
        :param max_results: The maximum number of results to return
        :type max_results: int
        :param types: The list of allowed result elements
        :type types: list
        
        """
        label_strings = []
        for label in labels:
            if inspect.isclass(label) and issubclass(label, Edge):
                label_string = label.get_label()
            elif isinstance(label, Edge):
                label_string = label.get_label()
            elif isinstance(label, basestring):
                label_string = label
            else:
                raise ThunderdomeException('traversal labels must be edge classes, instances, or strings')
            label_strings.append(label_string)

        allowed_elts = None
        if types is not None:
            allowed_elts = []
            for e in types:
                if issubclass(e, Vertex):
                    allowed_elts += [e.get_element_type()]
                elif issubclass(e, Edge):
                    allowed_elts += [e.get_label()]

        if limit is not None and offset is not None:
            start = offset
            end = offset + limit
        else:
            start = end = None
        
        return self._traversal(operation,
                               label_strings,
                               start,
                               end,
                               allowed_elts)

    def _simple_deletion(self, operation, labels):
        """
        Perform simple bulk graph deletion operation.

        :param operation: The operation to be performed
        :type operation: str
        :param label: The edge label to be used
        :type label: str or Edge
        
        """
        label_strings = []
        for label in labels:
            if inspect.isclass(label) and issubclass(label, Edge):
                label_string = label.get_label()
            elif isinstance(label, Edge):
                label_string = label.get_label()
            label_strings.append(label_string)

        return self._delete_related(operation, label_strings)

    def outV(self, *labels, **kwargs):
        """
        Return a list of vertices reached by traversing the outgoing edge with
        the given label.
        
        :param labels: pass in the labels to follow in as positional arguments
        :type labels: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list
        
        """
        return self._simple_traversal('outV', labels, **kwargs)

    def inV(self, *labels, **kwargs):
        """
        Return a list of vertices reached by traversing the incoming edge with
        the given label.
        
        :param label: The edge label to be traversed
        :type label: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list

        """
        return self._simple_traversal('inV', labels, **kwargs)

    def outE(self, *labels, **kwargs):
        """
        Return a list of edges with the given label going out of this vertex.
        
        :param label: The edge label to be traversed
        :type label: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list
        
        """
        return self._simple_traversal('outE', labels, **kwargs)

    def inE(self, *labels, **kwargs):
        """
        Return a list of edges with the given label coming into this vertex.
        
        :param label: The edge label to be traversed
        :type label: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list
        
        """
        return self._simple_traversal('inE', labels, **kwargs)

    def bothE(self, *labels, **kwargs):
        """
        Return a list of edges both incoming and outgoing from this vertex.

        :param label: The edge label to be traversed (optional)
        :type label: str or BaseEdge or None
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list
        
        """
        return self._simple_traversal('bothE', labels, **kwargs)

    def bothV(self, *labels, **kwargs):
        """
        Return a list of vertices both incoming and outgoing from this vertex.

        :param label: The edge label to be traversed (optional)
        :type label: str or BaseEdge or None
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param types: A list of allowed element types
        :type types: list
        
        """
        return self._simple_traversal('bothV', labels, **kwargs)


    def delete_outE(self, *labels):
        """Delete all outgoing edges with the given label."""
        self._simple_deletion('outE', labels)

    def delete_inE(self, *labels):
        """Delete all incoming edges with the given label."""
        self._simple_deletion('inE', labels)

    def delete_outV(self, *labels):
        """Delete all outgoing vertices connected with edges with the given label."""
        self._simple_deletion('outV', labels)

    def delete_inV(self, *labels):
        """Delete all incoming vertices connected with edges with the given label."""
        self._simple_deletion('inV', labels)

    def query(self):
        return Query(self)

        
        
def to_offset(page_num, per_page):
    """
    Convert a page_num and per_page to offset.

    :param page_num: The current page number
    :type page_num: int
    :param per_page: The maximum number of results per page
    :type per_page: int
    :rtype: int
    
    """
    if page_num and per_page:
        return (page_num-1) * per_page
    else:
        return None
    
    
class PaginatedVertex(Vertex):
    """
    Convenience class to easily handle pagination for traversals
    """

    @staticmethod
    def _transform_kwargs(kwargs):
        """
        Transforms paginated kwargs into limit/offset kwargs
        :param kwargs:
        :return:
        """
        values = kwargs.copy()
        return {
            'limit': kwargs.get('per_page'),
            'offset': to_offset(kwargs.get('page_num'), kwargs.get('per_page')),
            'types': kwargs.get('types'),
        }

    __abstract__ = True
    def outV(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).outV(*labels, **self._transform_kwargs(kwargs))
    
    def outE(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).outE(*labels, **self._transform_kwargs(kwargs))
            
    def inV(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).inV(*labels, **self._transform_kwargs(kwargs))
    
    def inE(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).inE(*labels, **self._transform_kwargs(kwargs))
    
    def bothV(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).bothV(*labels, **self._transform_kwargs(kwargs))
    
    def bothE(self, *labels, **kwargs):
        """
        :param labels: pass in the labels to follow in as positional arguments
        :param page_num: the page number to return
        :param per_page: the number of objects to return per page
        :param types: the element types this method is allowed to return
        :return:
        """
        return super(PaginatedVertex, self).bothE(*labels, **self._transform_kwargs(kwargs))
    
    
class EdgeMetaClass(ElementMetaClass):
    """Metaclass for edges."""
    
    def __new__(cls, name, bases, attrs):
        #short circuit element_type inheritance
        attrs['label'] = attrs.pop('label', None)

        klass = super(EdgeMetaClass, cls).__new__(cls, name, bases, attrs)

        if not klass.__abstract__:
            label = klass.get_label()
            if label in edge_types and str(edge_types[label]) != str(klass):
                raise ElementDefinitionException('{} is already registered as an edge'.format(label))
            edge_types[klass.get_label()] = klass
        return klass

    
class Edge(Element):
    """Base class for all edges."""
    
    __metaclass__ = EdgeMetaClass
    __abstract__ = True

    # if set to True, no more than one edge will
    # be created between two vertices
    __exclusive__ = False
    
    label = None
    
    gremlin_path = 'edge.groovy'
    
    _save_edge = GremlinMethod()
    _get_edges_between = GremlinMethod(classmethod=True)
    
    def __init__(self, outV, inV, **values):
        """
        Initialize this edge with the outgoing and incoming vertices as well as
        edge properties.

        :param outV: The vertex this edge is coming out of
        :type outV: Vertex
        :param inV: The vertex this edge is going into
        :type inV: Vertex
        :param values: The properties for this edge
        :type values: dict
        
        """
        self._outV = outV
        self._inV = inV
        super(Edge, self).__init__(**values)
        
    @classmethod
    def get_label(cls):
        """
        Returns the label for this edge.

        :rtype: str
        
        """
        return cls._type_name(cls.label)
    
    @classmethod
    def get_between(cls, outV, inV, page_num=None, per_page=None):
        """
        Return all the edges with a given label between two vertices.
        
        :param outV: The vertex the edge comes out of.
        :type outV: Vertex
        :param inV: The vertex the edge goes into.
        :type inV: Vertex
        :param page_num: The page number of the results
        :type page_num: int
        :param per_page: The number of results per page
        :type per_page : int
        :rtype: list
        
        """
        return cls._get_edges_between(out_v=outV,
                                      in_v=inV,
                                      label=cls.get_label(),
                                      page_num=page_num,
                                      per_page=per_page)
    
    def validate(self):
        """
        Perform validation of this edge raising a ValidationError if any
        problems are encountered.
        """
        if self.eid is None:
            if self._inV is None:
                raise ValidationError('in vertex must be set before saving new edges')
            if self._outV is None:
                raise ValidationError('out vertex must be set before saving new edges')
        super(Edge, self).validate()
        
    def save(self, *args, **kwargs):
        """
        Save this edge to the graph database.
        """
        super(Edge, self).save(*args, **kwargs)
        return self._save_edge(self._outV,
                               self._inV,
                               self.get_label(),
                               self.as_save_params(),
                               exclusive=self.__exclusive__)[0]

    def _reload_values(self):
        """
        Re-read the values for this edge from the graph database.
        """
        results = execute_query('g.e(eid)', {'eid':self.eid})[0]
        del results['_id']
        del results['_type']
        return results

    @classmethod
    def get_by_eid(cls, eid):
        """
        Return the edge with the given Titan-specific eid. Raises a
        DoesNotExist exception if no edge is found.

        :param eid: The Titan-specific edge id (eid)
        :type eid: int
        
        """
        results = execute_query('g.e(eid)', {'eid':eid})
        if not results:
            raise cls.DoesNotExist
        return Element.deserialize(results[0])

    @classmethod
    def create(cls, outV, inV, *args, **kwargs):
        """
        Create a new edge of the current type coming out of vertex outV and
        going into vertex inV with the given properties.

        :param outV: The vertex the edge is coming out of
        :type outV: Vertex
        :param inV: The vertex the edge is going into
        :type inV: Vertex
        
        """
        return super(Edge, cls).create(outV, inV, *args, **kwargs)
    
    def delete(self):
        """
        Delete the current edge from the graph.
        """
        if self.__abstract__:
            raise ThunderdomeException('cant delete abstract elements')
        if self.eid is None:
            return self
        query = """
        e = g.e(eid)
        if (e != null) {
          g.removeEdge(e)
          g.stopTransaction(SUCCESS)
        }
        """        
        results = execute_query(query, {'eid':self.eid})

    def _simple_traversal(self, operation):
        """
        Perform a simple traversal starting from the current edge returning a
        list of results.

        :param operation: The operation to be performed
        :type operation: str
        :rtype: list
        
        """
        results = execute_query('g.e(eid).%s()'%operation, {'eid':self.eid})
        return [Element.deserialize(r) for r in results]
        
    def inV(self):
        """
        Return the vertex that this edge goes into.

        :rtype: Vertex
        
        """
        if self._inV is None:
            self._inV = self._simple_traversal('inV')
        elif isinstance(self._inV, (int, long)):
            self._inV = Vertex.get_by_eid(self._inV)
        return self._inV
    
    def outV(self):
        """
        Return the vertex that this edge is coming out of.

        :rtype: Vertex
        
        """
        if self._outV is None:
            self._outV = self._simple_traversal('outV')
        elif isinstance(self._outV, (int, long)):
            self._outV = Vertex.get_by_eid(self._outV)
        return self._outV



import copy

class Query(object):
    """
    All query operations return a new query object, which currently deviates from blueprints.
    The blueprints query object modifies and returns the same object
    This method seems more flexible, and consistent w/ the rest of Gremlin.
    """
    _limit = None

    def __init__(self, vertex):
        self._vertex = vertex
        self._has = []
        self._interval = []
        self._labels = []
        self._direction = []
        self._vars = {}

    def count(self):
        """
        :return: number of matching vertices
        :rtype int
        """
        return self._execute('count', deserialize=False)[0]

    def direction(self, direction):
        """
        :param direction:
        :rtype: Query
        """
        q = copy.copy(self)
        if self._direction:
            raise ThunderdomeQueryError("Direction already set")
        q._direction = direction
        return q

    def edges(self):
        """
        :return list of matching edges
        """
        return self._execute('edges')

    def has(self, key, value, compare=EQUAL):
        """
        :param key: str
        :param value: str, float, int
        :param compare:
        :rtype: Query
        """
        compare = "Query.Compare.{}".format(compare)

        q = copy.copy(self)
        q._has.append((key,value,compare))
        return q

    def interval(self, key, start, end):
        """
        :rtype : Query
        """
        if start > end:
            start, end = end, start

        q = copy.copy(self)
        q._interval.append((key, start, end))
        return q


    def labels(self, *args):
        """
        :param args: list of Edges
        :return: Query
        """
        tmp = []
        for x in args:
            try:
                tmp.append(x.get_label())
            except:
                tmp.append(x)

        q = copy.copy(self)
        q._labels = tmp
        return q

    def limit(self, limit):
        q = copy.copy(self)
        q._limit = limit
        return q

    def vertexIds(self):
        return self._execute('vertexIds', deserialize=False)

    def vertices(self):
        return self._execute('vertices')

    def _get_partial(self):
        limit = ".limit(limit)" if self._limit else ""
        dir = ".direction({})".format(self._direction) if self._direction else ""

        # do labels
        labels = ""
        if self._labels:
            labels = ["'{}'".format(x) for x in self._labels]
            labels = ", ".join(labels)
            labels = ".labels({})".format(labels)

        ### construct has clauses
        has = []

        for x in self._has:
            c = "v{}".format(len(self._vars))
            self._vars[c] = x[1]

            val = "{} as double".format(c) if isinstance(x[1], float) else c
            key = x[0]
            has.append("has('{}', {}, {})".format(key, val, x[2]))

        if has:
            tmp = ".".join(has)
            has = '.{}'.format(tmp)
        else:
            has = ""
        ### end construct has clauses

        intervals = []
        for x in self._interval:
            c = "v{}".format(len(self._vars))
            self._vars[c] = x[1]
            c2 = "v{}".format(len(self._vars))
            self._vars[c2] = x[2]


            val1 = "{} as double".format(c) if isinstance(x[1], float) else c
            val2 = "{} as double".format(c2) if isinstance(x[2], float) else c2

            tmp = "interval('{}', {}, {})".format(x[0], val1, val2)
            intervals.append(tmp)

        if intervals:
            intervals = ".{}".format(".".join(intervals))
        else:
            intervals = ""

        return "g.v(eid).query(){}{}{}{}{}".format(labels, limit, dir, has, intervals)

    def _execute(self, func, deserialize=True):
        tmp = "{}.{}()".format(self._get_partial(), func)
        self._vars.update({"eid":self._vertex.eid, "limit":self._limit})
        results = execute_query(tmp, self._vars)

        if deserialize:
            return  [Element.deserialize(r) for r in results]
        else:
            return results






