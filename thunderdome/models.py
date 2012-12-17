from collections import OrderedDict
import re
from uuid import UUID

from thunderdome import columns
from thunderdome.connection import execute_query, ThunderdomeQueryError
from thunderdome.exceptions import ModelException
from thunderdome.query import QuerySet, QueryException

#dict of node and edge types for rehydrating results
vertex_types = {}
edge_types = {}

class ElementDefinitionException(ModelException): pass

class BaseElement(object):
    """
    The base model class, don't inherit from this, inherit from Model, defined below
    """
    
    class DoesNotExist(QueryException): pass
    class MultipleObjectsReturned(QueryException): pass

    def __init__(self, **values):
        self.eid = values.get('_id')
        self._values = {}
        for name, column in self._columns.items():
            value =  values.get(name, None)
            if value is not None: value = column.to_python(value)
            value_mngr = column.value_manager(self, column, value)
            self._values[name] = value_mngr

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
            setattr(self, name, val)

    def as_dict(self):
        """ Returns a map of column names to cleaned values """
        values = {}
        for name, col in self._columns.items():
            values[name] = col.to_database(getattr(self, name, None))
        return values

    @classmethod
    def create(cls, **kwargs):
        return cls(**kwargs).save()
        
    
    @classmethod
    def all(cls):
        return cls.objects.all()
    
    @classmethod
    def filter(cls, **kwargs):
        return cls.objects.filter(**kwargs)
    
    @classmethod
    def get(cls, **kwargs):
        return cls.objects.get(**kwargs)

    def _create(self):
        raise NotImplementedError

    def _update(self):
        raise NotImplementedError
    
    def save(self):
        is_new = self.eid is None
        self.validate()
        return self

    def delete(self):
        """ Deletes this instance """
        self.objects.delete_instance(self)

class ElementMetaClass(type):

    def __new__(cls, name, bases, attrs):
        """
        """
        #move column definitions into columns dict
        #and set default column names
        column_dict = OrderedDict()

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

        #create the class and add a QuerySet to it
        klass = super(ElementMetaClass, cls).__new__(cls, name, bases, attrs)
        return klass


class Element(BaseElement):
    """
    the db name for the column family can be set as the attribute db_name, or
    it will be genertaed from the class name
    """
    __metaclass__ = ElementMetaClass
    
    
class VertexMetaClass(ElementMetaClass):
    def __new__(cls, name, bases, attrs):
        klass = super(VertexMetaClass, cls).__new__(cls, name, bases, attrs)
        
        element_type = klass.get_element_type()
        if element_type in vertex_types:
            raise ElementDefinitionException('{} is already registered as a vertex'.format(element_type))
        vertex_types[element_type] = klass
        return klass
        
class Vertex(Element):
    
    __metaclass__ = VertexMetaClass
    
    element_type = None
    
    @classmethod
    def get_element_type(cls):
        return cls._type_name(cls.element_type)
    
    @classmethod
    def all(cls, vids, as_dict=False):
        if not isinstance(vids, (list, tuple)):
            raise ThunderdomeQueryError("vids must be of type list or tuple")
        
        strvids = [str(v) for v in vids]
        qs = ['vs = vids.collect{g.V("vid", it).toList()[0]}']
        qs += ['vs.collect{it.map.toSet()}.flatten()']
        
        results = execute_query('\n'.join(qs), {'vids':strvids})
        results = filter(None, results)
        
        if len(results) != len(vids):
            raise ThunderdomeQueryError("the number of results don't match the number of vids requested")
        
        objects = []
        for r in results:
            etype = r['element_type']
            try:
                objects += [vertex_types[etype](**r)]
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
            return results[0]
        except ThunderdomeQueryError:
            raise cls.DoesNotExist
        
    
    def save(self, *args, **kwargs):
        super(Vertex, self).save(*args, **kwargs)
        
        qs = ['g.stopTransaction(SUCCESS)']
        params = {}
        if self.eid is None:
            qs += ['v = g.addVertex()']
        else:
            qs += ['v = g.v(eid)']
            params['eid'] = self.eid
            
        values = self.as_dict()
        qs += ['v.setProperty("element_type", element_type)']
        params['element_type'] = self.get_element_type()
        for name, col in self._columns.items():
            val = values.get(name)
            val = col.to_database(val)
            valname = name + '_val'
            qs += ['v.setProperty("{}", {})'.format(col.db_field_name, valname)]
            params[valname] = val
            

        qs += ['data = v.map.toSet()']
        qs += ['g.stopTransaction(SUCCESS)']
        qs += ['g.getVertex(v)']
        
        results = execute_query('\n'.join(qs), params, transaction=False)
        
        assert len(results) == 1
        self.eid = results[0].get('_id')
        return self
    
    def delete(self):
        if self.eid is None:
            raise ThunderdomeQueryError("Can't delete vertices that haven't been saved")
        results = execute_query('g.removeVertex(g.v(eid))', {'eid': self.eid})
        
    
class EdgeMetaClass(ElementMetaClass):
    def __new__(cls, name, bases, attrs):
        klass = super(EdgeMetaClass, cls).__new__(cls, name, bases, attrs)
        
        label = klass.get_label()
        if label in edge_types:
            raise ElementDefinitionException('{} is already registered as an edge'.format(element_type))
        edge_types[klass.get_label()] = klass
        return klass
        
class Edge(Element):
    
    __metaclass__ = EdgeMetaClass
    
    label = None
    
    @classmethod
    def get_label(cls):
        return cls._type_name(cls.label)


