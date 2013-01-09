from collections import OrderedDict
import inspect
import re
from uuid import UUID

from thunderdome import columns
from thunderdome.connection import execute_query, ThunderdomeQueryError
from thunderdome.exceptions import ModelException, ValidationError, DoesNotExist, MultipleObjectsReturned, ThunderdomeException, WrongElementType
from thunderdome.gremlin import BaseGremlinMethod, GremlinMethod

#dict of node and edge types for rehydrating results
vertex_types = {}
edge_types = {}

class ElementDefinitionException(ModelException): pass

class BaseElement(object):
    """
    The base model class, don't inherit from this, inherit from Model, defined below
    """
    
    class DoesNotExist(DoesNotExist): pass
    class MultipleObjectsReturned(MultipleObjectsReturned): pass
    class WrongElementType(WrongElementType): pass

    def __init__(self, **values):
        self.eid = values.get('_id')
        self._values = {}
        for name, column in self._columns.items():
            value =  values.get(name, None)
            if value is not None: value = column.to_python(value)
            value_mngr = column.value_manager(self, column, value)
            self._values[name] = value_mngr

    def __eq__(self, other):
        return self.as_dict() == other.as_dict() and self.eid == other.eid

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def _type_name(cls, manual_name):
        """
        Returns the column family name if it's been defined
        otherwise, it creates it from the module and class name
        """
        cf_name = ''
        if manual_name:
            cf_name = manual_name.lower()
        else:
            camelcase = re.compile(r'([a-z])([A-Z])')
            ccase = lambda s: camelcase.sub(lambda v: '{}_{}'.format(v.group(1), v.group(2).lower()), s)
    
            cf_name += ccase(cls.__name__)
            cf_name = cf_name.lower()
        return cf_name

    def validate(self):
        """ Cleans and validates the field values """
        for name, col in self._columns.items():
            val = col.validate(getattr(self, name))
            func_name = 'validate_{}'.format(name)
            if hasattr(self, func_name):
                val = getattr(self, func_name)(val)
            setattr(self, name, val)

    def as_dict(self):
        """ Returns a map of column names to cleaned values """
        values = {}
        for name, col in self._columns.items():
            values[name] = col.to_database(getattr(self, name, None))
        return values

    @classmethod
    def create(cls, *args, **kwargs):
        return cls(*args, **kwargs).save()
        
    def pre_save(self):
        self.validate()
        
    def save(self):
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

class ElementMetaClass(type):

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
    def __new__(cls, name, bases, attrs):

        #short circuit element_type inheritance
        attrs['element_type'] = attrs.pop('element_type', None)

        klass = super(VertexMetaClass, cls).__new__(cls, name, bases, attrs)

        if not klass.__abstract__:
            element_type = klass.get_element_type()
            if element_type in vertex_types:
                raise ElementDefinitionException('{} is already registered as a vertex'.format(element_type))
            vertex_types[element_type] = klass
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
    vid = columns.UUID()
    
    element_type = None
    
    @classmethod
    def get_element_type(cls):
        return cls._type_name(cls.element_type)
    
    @classmethod
    def all(cls, vids, as_dict=False):
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
    
    @classmethod
    def get(cls, vid):
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
        results = execute_query('g.v(eid)', {'eid':eid})
        if not results:
            raise cls.DoesNotExist
        return Element.deserialize(results[0])
    
    def save(self, *args, **kwargs):
        super(Vertex, self).save(*args, **kwargs)
        params = self.as_dict()
        params['element_type'] = self.get_element_type()
        result = self._save_vertex(params)[0]
        self.eid = result.eid
        return self
    
    def delete(self):
        if self.__abstract__:
            raise ThunderdomeException('cant delete abstract elements')
        if self.eid is None:
            return self
        query = """
        g.removeVertex(g.v(eid))
        g.stopTransaction(SUCCESS)
        """
        results = execute_query(query, {'eid': self.eid})
        
    def _simple_traversal(self, operation, label, page_num=None, per_page=None):
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
        
        """
        if inspect.isclass(label) and issubclass(label, Edge):
            label = label.get_label()
        elif isinstance(label, Edge):
            label = label.get_label()

        return self._traversal(operation, label, page_num, per_page)

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

    def outV(self, label=None, page_num=None, per_page=None):
        return self._simple_traversal('outV', label, page_num, per_page)

    def inV(self, label=None, page_num=None, per_page=None):
        return self._simple_traversal('inV', label, page_num, per_page)

    def outE(self, label=None, page_num=None, per_page=None):
        return self._simple_traversal('outE', label, page_num, per_page)

    def inE(self, label=None, page_num=None, per_page=None):
        return self._simple_traversal('inE', label, page_num, per_page)

    def delete_outE(self, label=None):
        self._simple_deletion('outE', label)

    def delete_inE(self, label=None):
        self._simple_deletion('inE', label)

    def delete_outV(self, label=None):
        self._simple_deletion('outV', label)

    def delete_inV(self, label=None):
        self._simple_deletion('inV', label)
        

class EdgeMetaClass(ElementMetaClass):
    def __new__(cls, name, bases, attrs):

        #short circuit element_type inheritance
        attrs['label'] = attrs.pop('label', None)

        klass = super(EdgeMetaClass, cls).__new__(cls, name, bases, attrs)

        if not klass.__abstract__:
            label = klass.get_label()
            if label in edge_types:
                raise ElementDefinitionException('{} is already registered as an edge'.format(label))
            edge_types[klass.get_label()] = klass
        return klass
        
class Edge(Element):
    
    __metaclass__ = EdgeMetaClass
    __abstract__ = True
    
    label = None
    
    gremlin_path = 'edge.groovy'
    
    _save_edge = GremlinMethod()
    _get_edges_between = GremlinMethod(classmethod=True)
    
    def __init__(self, outV, inV, **values):
        self._outV = outV
        self._inV = inV
        super(Edge, self).__init__(**values)
        
    @classmethod
    def get_label(cls):
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
        if self.eid is None:
            if self._inV is None:
                raise ValidationError('in vertex must be set before saving new edges')
            if self._outV is None:
                raise ValidationError('out vertex must be set before saving new edges')
        super(Edge, self).validate()
        
    def save(self, exclusive=True, *args, **kwargs):
        """
        :param exclusive: if set to True, will not create multiple edges between 2 vertices with the same label
        """
        super(Edge, self).save(*args, **kwargs)
        return self._save_edge(self._outV,
                               self._inV,
                               self.get_label(),
                               self.as_dict(),
                               exclusive=exclusive)[0]
        
    @classmethod
    def create(cls, outV, inV, *args, **kwargs):
        return super(Edge, cls).create(outV, inV, *args, **kwargs)
    
    def delete(self):
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
        results = execute_query('g.e(eid).%s()'%operation, {'eid':self.eid})
        return [Element.deserialize(r) for r in results]
        
    @property
    def inV(self):
        if self._inV is None:
            self._inV = self._simple_traversal('inV')
        elif isinstance(self._inV, (int, long)):
            self._inV = Vertex.get_by_eid(self._inV)
        return self._inV
    
    @property
    def outV(self):
        if self._outV is None:
            self._outV = self._simple_traversal('outV')
        elif isinstance(self._outV, (int, long)):
            self._outV = Vertex.get_by_eid(self._outV)
        return self._outV
    
    










