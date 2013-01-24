from collections import OrderedDict
import inspect
import re
from uuid import UUID

from thunderdome import columns
from thunderdome.connection import execute_query, create_key_index, ThunderdomeQueryError
from thunderdome.exceptions import ModelException, ValidationError, DoesNotExist, MultipleObjectsReturned, ThunderdomeException, WrongElementType
from thunderdome.gremlin import BaseGremlinMethod, GremlinMethod


#dict of node and edge types for rehydrating results
vertex_types = {}
edge_types = {}


class ElementDefinitionException(ModelException): pass
class SaveStrategyException(ModelException): pass


class BaseElement(object):
    """
    The base model class, don't inherit from this, inherit from Model, defined below
    """

    # When true this will prepend the module name to the type name of the class
    __use_module_name__ = False
    __default_save_strategy__ = columns.SAVE_ALWAYS
    
    class DoesNotExist(DoesNotExist): pass
    class MultipleObjectsReturned(MultipleObjectsReturned): pass
    class WrongElementType(WrongElementType): pass

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
            if value is not None: value = column.to_python(value)
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
        Returns the column family name if it has been defined, otherwise it
        creates it from the module and class name.

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
            if col_strategy == columns.SAVE_ONCE:
                if was_saved:
                    if self._values[name].changed:
                        raise SaveStrategyException("Attempt to change column '{}' with save strategy SAVE_ONCE".format(name))
                    else:
                        should_save = False
            elif col_strategy == columns.SAVE_ONCHANGE:
                if was_saved and not self._values[name].changed:
                    should_save = False
            
            if should_save:
                values[name] = col.to_database(getattr(self, name, None))
                
        return values

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
        performs an update of this element with the given values and returns the saved object
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
            value = values.get(name, None)
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
                attrs[col_name] = property(_get, _set)
            else:
                attrs[col_name] = property(_get, _set, _del)

        column_definitions = [(k,v) for k,v in attrs.items() if isinstance(v, columns.Column)]
        column_definitions = sorted(column_definitions, lambda x,y: cmp(x[1].position, y[1].position))
        
        #TODO: check that the defined columns don't conflict with any of the Model API's existing attributes/methods
        #transform column definitions
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
    """
    the db name for the column family can be set as the attribute db_name, or
    it will be generated from the class name
    """
    __metaclass__ = ElementMetaClass
    
    @classmethod
    def deserialize(cls, data):
        """
        Deserializes rexster json into vertex or edge objects
        """
        dtype = data.get('_type')
        if dtype == 'vertex':
            vertex_type = data['element_type']
            return vertex_types[vertex_type](**data)
        elif dtype == 'edge':
            edge_type = data['_label']
            return edge_types[edge_type](data['_outV'], data['_inV'], **data)
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
    The Vertex model base class. All vertexes have a vid defined on them, the element type is autogenerated
    from the subclass name, but can optionally be set manually
    """
    __metaclass__ = VertexMetaClass
    __abstract__ = True

    gremlin_path = 'vertex.groovy'

    _save_vertex = GremlinMethod()
    _traversal = GremlinMethod()
    _delete_related = GremlinMethod()

    #vertex id
    vid = columns.UUID(save_strategy=columns.SAVE_ONCE)
    
    element_type = None

    @classmethod
    def _create_indices(cls):
        """
        Creates this model's indices. This will be skipped if connection.setup hasn't been
        called, but connection.setup calls this method on existing vertices
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
        return a dictionary containing vids as keys and vertices found as values.

        :param vids: A list of vids
        :type vids: list
        :param as_dict: Toggle whether or not to return a dictionary or list
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
        MultipleObjectsReturned exception if the vid corresponds to more
        than one vertex in the graph.

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
        Look update a vertex by its Titan-specific id (eid). Raises a DoesNotExist
        exception if a vertex with the given eid was not found.

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
                          label,
                          limit=None,
                          offset=None,
                          allowed_elements=None):
        """
        Perform simple graph database traversals with ubiquitous pagination.

        :param operation: The operation to be performed
        :type operation: str
        :param label: The edge label to be used
        :type label: str or Edge
        :param start: The starting offset
        :type start: int
        :param max_results: The maximum number of results to return
        :type max_results: int
        :param allowed_elements: The list of allowed result elements
        :type allowed_elements: list
        
        """
        if inspect.isclass(label) and issubclass(label, Edge):
            label = label.get_label()
        elif isinstance(label, Edge):
            label = label.get_label()

        allowed_elts = None
        if allowed_elements is not None:
            allowed_elts = []
            for e in allowed_elements:
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
                               label,
                               start,
                               end,
                               allowed_elts)

    def _simple_deletion(self, operation, label):
        """
        Perform simple bulk graph deletion operation.

        :param operation: The operation to be performed
        :type operation: str
        :param label: The edge label to be used
        :type label: str or Edge
        
        """
        if inspect.isclass(label) and issubclass(label, Edge):
            label = label.get_label()
        elif isinstance(label, Edge):
            label = label.get_label()

        return self._delete_related(operation, label)

    def outV(self,
             label=None,
             limit=None,
             offset=None,
             allowed_elements=None):
        """
        Return a list of vertices reached by traversing the outgoing edge
        with the given label.
        
        :param label: The edge label to be traversed
        :type label: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param allowed_elements: A list of allowed element types
        :type allowed_elements: list
        
        """
        return self._simple_traversal('outV',
                                      label,
                                      limit,
                                      offset,
                                      allowed_elements)

    def inV(self,
            label=None,
            limit=None,
            offset=None,
            allowed_elements=None):
        """
        Return a list of vertices reached by traversing the incoming edge
        with the given label.
        
        :param label: The edge label to be traversed
        :type label: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param allowed_elements: A list of allowed element types
        :type allowed_elements: list
        
        """
        return self._simple_traversal('inV',
                                      label,
                                      limit,
                                      offset,
                                      allowed_elements)

    def outE(self,
             label=None,
             limit=None,
             offset=None,
             allowed_elements=None):
        """
        Return a list of edges with the given label going out of this vertex.
        
        :param label: The edge label to be traversed
        :type label: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param allowed_elements: A list of allowed element types
        :type allowed_elements: list
        
        """
        return self._simple_traversal('outE',
                                      label,
                                      limit,
                                      offset,
                                      allowed_elements)

    def inE(self,
            label=None,
            limit=None,
            offset=None,
            allowed_elements=None):
        """
        Return a list of edges with the given label coming into this vertex.
        
        :param label: The edge label to be traversed
        :type label: str or BaseEdge
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param allowed_elements: A list of allowed element types
        :type allowed_elements: list
        
        """
        return self._simple_traversal('inE',
                                      label,
                                      limit,
                                      offset,
                                      allowed_elements)

    def bothE(self,
              label=None,
              limit=None,
              offset=None,
              allowed_elements=None):
        """
        Return a list of edges both incoming and outgoing from this vertex.

        :param label: The edge label to be traversed (optional)
        :type label: str or BaseEdge or None
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param allowed_elements: A list of allowed element types
        :type allowed_elements: list
        
        """
        return self._simple_traversal('bothE',
                                      label,
                                      limit,
                                      offset,
                                      allowed_elements)
    
    def bothV(self,
              label=None,
              limit=None,
              offset=None,
              allowed_elements=None):
        """
        Return a list of vertices both incoming and outgoing from this vertex.

        :param label: The edge label to be traversed (optional)
        :type label: str or BaseEdge or None
        :param limit: The number of the page to start returning results at
        :type limit: int or None
        :param offset: The maximum number of results to return
        :type offset: int or None
        :param allowed_elements: A list of allowed element types
        :type allowed_elements: list
        
        """
        return self._simple_traversal('bothV',
                                      label,
                                      limit,
                                      offset,
                                      allowed_elements)


    def delete_outE(self, label=None):
        """Delete all outgoing edges with the given label."""
        self._simple_deletion('outE', label)

    def delete_inE(self, label=None):
        """Delete all incoming edges with the given label."""
        self._simple_deletion('inE', label)

    def delete_outV(self, label=None):
        """Delete all outgoing vertices connected with edges with the given label."""
        self._simple_deletion('outV', label)

    def delete_inV(self, label=None):
        """Delete all incoming vertices connected with edges with the given label."""
        self._simple_deletion('inV', label)
        
        
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
    __abstract__ = True
    def outV(self,
         label=None,
         page_num=None,
         per_page=None,
         allowed_elements=None):
        return super(PaginatedVertex, self).outV(label, per_page, to_offset(page_num, per_page), allowed_elements)
    
    def outE(self,
         label=None,
         page_num=None,
         per_page=None,
         allowed_elements=None):
        return super(PaginatedVertex, self).outE(label, per_page, to_offset(page_num, per_page), allowed_elements)
            
    def inV(self,
         label=None,
         page_num=None,
         per_page=None,
         allowed_elements=None):
        return super(PaginatedVertex, self).inV(label, per_page, to_offset(page_num, per_page), allowed_elements)
    
    def inE(self,
         label=None,
         page_num=None,
         per_page=None,
         allowed_elements=None):
        return super(PaginatedVertex, self).inE(label, per_page, to_offset(page_num, per_page), allowed_elements)
    
    def bothV(self,
         label=None,
         page_num=None,
         per_page=None,
         allowed_elements=None):
        return super(PaginatedVertex, self).bothV(label, per_page, to_offset(page_num, per_page), allowed_elements)
    
    def bothE(self,
         label=None,
         page_num=None,
         per_page=None,
         allowed_elements=None):
        return super(PaginatedVertex, self).bothE(label, per_page, to_offset(page_num, per_page), allowed_elements)
    
    
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
        Initialize this edge with the outgoing and incoming vertices as well
        as edge properties.

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
        return cls._get_edges_between(outV=outV, inV=inV,
                                      label=cls.get_label(),
                                      page_num=page_num,
                                      per_page=per_page)
    
    def validate(self):
        """
        Perform validation of this edge raising a ValidationError if any problems
        are encountered.
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
        g.removeEdge(g.e(eid))
        g.stopTransaction(SUCCESS)
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
