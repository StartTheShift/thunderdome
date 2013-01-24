#column field types
from datetime import datetime
from decimal import Decimal as D
import re
import time
from uuid import uuid1, uuid4
from uuid import UUID as _UUID

from thunderdome.exceptions import ValidationError

"""
Saving strategies for thunderdome. These are used to indicate when a property
should be saved after the initial vertex/edge creation.
"""
SAVE_ONCE     = 1
SAVE_ONCHANGE = 2
SAVE_ALWAYS   = 3

    
class StringComparableUUID(_UUID):
    """UUID type that can be compared against strings"""
    
    def __eq__(self, other):
        """ Handle string comparisons for UUIDs so people don't have to explicitly cast """
        if isinstance(other, basestring):
            return str(self) == other
        return str(self) == str(other)

    
class BaseValueManager(object):
    """
    Value managers are used to manage values pulled from the database and
    track state changes.
    """
    
    def __init__(self, instance, column, value):
        """
        Initialize the value manager.

        :param instance: An object instance
        :type instance: mixed
        :param column: The column to manage
        :type column: thunder.columns.Column
        :param value: The initial value of the column
        :type value: mixed
        
        """
        self.instance = instance
        self.column = column
        self.previous_value = value
        self.value = value

    @property
    def deleted(self):
        """
        Indicates whether or not this value has been deleted.

        :rtype: boolean
        
        """
        return self.value is None and self.previous_value is not None

    @property
    def changed(self):
        """
        Indicates whether or not this value has changed.

        :rtype: boolean
        
        """
        return self.value != self.previous_value

    def getval(self):
        """Return the current value."""
        return self.value

    def setval(self, val):
        """
        Updates the current value.

        :param val: The new value
        :type val: mixed
        
        """
        self.value = val

    def delval(self):
        """Delete a given value"""
        self.value = None

    def get_property(self):
        """
        Returns a value-managed property attributes

        :rtype: property
        
        """
        _get = lambda slf: self.getval()
        _set = lambda slf, val: self.setval(val)
        _del = lambda slf: self.delval()

        if self.column.can_delete:
            return property(_get, _set, _del)
        else:
            return property(_get, _set)

        
class Column(object):

    #the cassandra type this column maps to
    db_type = None
    value_manager = BaseValueManager

    instance_counter = 0

    def __init__(self,
                 primary_key=False,
                 index=False,
                 db_field=None,
                 default=None,
                 required=False,
                 save_strategy=None):
        """
        Initialize this column with the given information.
        
        :param primary_key: bool flag, indicates this column is a primary key. The first primary key defined
        on a model is the partition key, all others are cluster keys
        :param index: bool flag, indicates an index should be created for this column
        :param db_field: the fieldname this field will map to in the database
        :param default: the default value, can be a value or a callable (no args)
        :param required: boolean, is the field required?
        :param save_strategy: Strategy used when persisting the value of the column
        :type save_strategy: int
        
        """
        self.primary_key = primary_key
        self.index = index
        self.db_field = db_field
        self.default = default
        self.required = required
        self.save_strategy = save_strategy

        #the column name in the model definition
        self.column_name = None

        self.value = None

        #keep track of instantiation order
        self.position = Column.instance_counter
        Column.instance_counter += 1

    def validate(self, value):
        """
        Returns a cleaned and validated value. Raises a ValidationError
        if there's a problem
        """
        if value is None:
            if self.has_default:
                return self.get_default()
            elif self.required:
                raise ValidationError('{} - None values are not allowed'.format(self.column_name or self.db_field))
        return value

    def to_python(self, value):
        """
        Converts data from the database into python values
        raises a ValidationError if the value can't be converted
        """
        return value

    def to_database(self, value):
        """
        Converts python value into database value
        """
        if value is None and self.has_default:
            return self.get_default()
        return value

    @property
    def has_default(self):
        """
        Indicates whether or not this column has a default value.

        :rtype: boolean

        """
        return self.default is not None

    @property
    def has_save_strategy(self):
        """
        Indicates whether or not this column has a save strategy.

        :rtype: boolean
        
        """
        return self.save_strategy is not None

    @property
    def is_primary_key(self):
        """
        Indicates whether or not this column is a primary key.

        :rtype: boolean
        
        """
        return self.primary_key

    @property
    def can_delete(self):
        return not self.primary_key

    def get_save_strategy(self):
        """
        Returns the save strategy attached to this column.

        :rtype: int or None
        
        """
        return self.save_strategy
    
    def get_default(self):
        if self.has_default:
            if callable(self.default):
                return self.default()
            else:
                return self.default

    def get_column_def(self):
        """
        Returns a column definition for CQL table definition
        """
        return '{} {}'.format(self.db_field_name, self.db_type)

    def set_column_name(self, name):
        """
        Sets the column name during document class construction
        This value will be ignored if db_field is set in __init__
        """
        self.column_name = name

    @property
    def db_field_name(self):
        """ Returns the name of the cql name of this column """
        return self.db_field or self.column_name

    @property
    def db_index_name(self):
        """ Returns the name of the cql index """
        return 'index_{}'.format(self.db_field_name)

    
class Bytes(Column):
    db_type = 'blob'

    
class Ascii(Column):
    db_type = 'ascii'

    
class Text(Column):
    db_type = 'text'
    
    def __init__(self, *args, **kwargs):
        self.min_length = kwargs.pop('min_length', 1 if kwargs.get('required', True) else None)
        self.max_length = kwargs.pop('max_length', None)
        super(Text, self).__init__(*args, **kwargs)

    def validate(self, value):
        value = super(Text, self).validate(value)
        # we've already done the required check in validate
        if value is None:
            return None
        
        if not isinstance(value, basestring) and value is not None:
            raise ValidationError('{} is not a string'.format(type(value)))
        if self.max_length:
            if len(value) > self.max_length:
                raise ValidationError('{} is longer than {} characters'.format(self.column_name, self.max_length))
        if self.min_length:
            if len(value) < self.min_length:
                raise ValidationError('{} is shorter than {} characters'.format(self.column_name, self.min_length))
        return value

    
class Integer(Column):
    db_type = 'int'

    def validate(self, value):
        val = super(Integer, self).validate(value)
        if val is None: return
        try:
            return long(val)
        except (TypeError, ValueError):
            raise ValidationError("{} can't be converted to integral value".format(value))

    def to_python(self, value):
        if value is not None:
            return long(value)

    def to_database(self, value):
        if value is not None:
            return long(value)

        
class DateTime(Column):
    db_type = 'timestamp'
    def __init__(self, **kwargs):
        super(DateTime, self).__init__(**kwargs)

    def to_python(self, value):
        if isinstance(value, datetime):
            return value
        return datetime.fromtimestamp(float(value))

    def to_database(self, value):
        value = super(DateTime, self).to_database(value)
        if value is None: return
        if not isinstance(value, datetime):
            raise ValidationError("'{}' is not a datetime object".format(value))
        return time.mktime(value.timetuple())

    
class UUID(Column):
    """
    Type 1 or 4 UUID
    """

    db_type = 'uuid'

    re_uuid = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

    def __init__(self, default=lambda:StringComparableUUID(str(uuid4())), **kwargs):
        super(UUID, self).__init__(default=default, **kwargs)

    def validate(self, value):
        val = super(UUID, self).validate(value)
        
        if val is None: return None # if required = False and not given
        if not self.re_uuid.match(str(val)):
            raise ValidationError("{} is not a valid uuid".format(value))
        return val
    
    def to_python(self, value):
        val = super(UUID, self).to_python(value)
        return str(val)
    
    def to_database(self, value):
        val = super(UUID, self).to_database(value)
        if value is None: return
        return str(val)

    
class Boolean(Column):
    db_type = 'boolean'

    def to_python(self, value):
        return bool(value)

    def to_database(self, value):
        return bool(value)

    
class Float(Column):
    db_type = 'double'

    def __init__(self, double_precision=True, **kwargs):
        self.db_type = 'double' if double_precision else 'float'
        super(Float, self).__init__(**kwargs)

    def validate(self, value):
        val = super(Float, self).validate(value)
        if val is None: return None # required = False
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValidationError("{} is not a valid float".format(value))

    def to_python(self, value):
        if value is not None:
            return float(value)

    def to_database(self, value):
        if value is not None:
            return float(value)

        
class Decimal(Column):
    db_type = 'decimal'
    
    def to_python(self, value):
        val = super(Decimal, self).to_python(value)
        if val is not None:
            return D(val)

    def to_database(self, value):
        val = super(Decimal, self).to_database(value)
        if val is not None:
            return str(val)

        
class Dictionary(Column):

    def validate(self, value):
        val = super(Dictionary, self).validate(value)
        if val is None: return None # required = False
        if not isinstance(val, dict):
            raise ValidationError('{} is not a valid dict'.format(val))
        return val

    
class List(Column):

    def validate(self, value):
        val = super(List, self).validate(value)
        if val is None: return None # required = False
        if not isinstance(val, (list, tuple)):
            raise ValidationError('{} is not a valid list'.format(val))
        return val

