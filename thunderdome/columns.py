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

SAVE_ONCE     - Only save this value once. If it changes throw an exception.
SAVE_ONCHANGE - Only save this value if it has changed.
SAVE_ALWAYS   - Save this value every time the corresponding model is saved.

"""
SAVE_ONCE = 1
SAVE_ONCHANGE = 2
SAVE_ALWAYS = 3


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
    """Base class for column types"""

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

        :param primary_key: Indicates whether or not this is primary key
        :type primary_key: boolean
        :param index: Indicates whether or not this field should be indexed
        :type index: boolean
        :param db_field: The fieldname this field will map to in the database
        :type db_field: str
        :param default: Value or callable with no args to set default value
        :type default: mixed or callable
        :param required: Whether or not this field is required
        :type required: boolean
        :param save_strategy: Strategy used when saving the value of the column
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
    def can_delete(self):
        return not self.primary_key

    def get_save_strategy(self):
        """
        Returns the save strategy attached to this column.

        :rtype: int or None

        """
        return self.save_strategy

    def get_default(self):
        """
        Returns the default value for this column if one is available.

        :rtype: mixed or None

        """
        if self.has_default:
            if callable(self.default):
                return self.default()
            else:
                return self.default

    def set_column_name(self, name):
        """
        Sets the column name during document class construction This value will
        be ignored if db_field is set in __init__

        :param name: The name of this column
        :type name: str

        """
        self.column_name = name

    @property
    def db_field_name(self):
        """Returns the name of the thunderdome name of this column"""
        return self.db_field or self.column_name


class Text(Column):

    def __init__(self, *args, **kwargs):
        required = kwargs.get('required', True)
        self.min_length = kwargs.pop('min_length', 1 if required else None)
        self.max_length = kwargs.pop('max_length', None)
        super(Text, self).__init__(*args, **kwargs)

    def validate(self, value):
        value = super(Text, self).validate(value)

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

    def validate(self, value):
        val = super(Integer, self).validate(value)

        if val is None:
            return

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

    def __init__(self, **kwargs):
        super(DateTime, self).__init__(**kwargs)

    def to_python(self, value):
        if isinstance(value, datetime):
            return value
        return datetime.fromtimestamp(float(value))

    def to_database(self, value):
        value = super(DateTime, self).to_database(value)
        if value is None:
            return
        if not isinstance(value, datetime):
            raise ValidationError("'{}' is not a datetime object".format(value))
        return time.mktime(value.timetuple())


class UUID(Column):
    """Universally Unique Identifier (UUID) type - UUID4 by default"""
    
    re_uuid = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

    def __init__(self, default=lambda: str(uuid4()), **kwargs):
        super(UUID, self).__init__(default=default, **kwargs)

    def validate(self, value):
        val = super(UUID, self).validate(value)

        if val is None:
            return None  # if required = False and not given
        if not self.re_uuid.match(str(val)):
            raise ValidationError("{} is not a valid uuid".format(value))
        return val

    def to_python(self, value):
        val = super(UUID, self).to_python(value)
        return str(val)

    def to_database(self, value):
        val = super(UUID, self).to_database(value)
        if value is None:
            return
        return str(val)


class Boolean(Column):

    def to_python(self, value):
        return bool(value)

    def to_database(self, value):
        return bool(value)


class Float(Column):

    def __init__(self, double_precision=True, **kwargs):
        self.db_type = 'double' if double_precision else 'float'
        super(Float, self).__init__(**kwargs)

    def validate(self, value):
        val = super(Float, self).validate(value)
        if val is None:
            return None  # required = False
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
        if val is None:
            return None  # required = False
        if not isinstance(val, dict):
            raise ValidationError('{} is not a valid dict'.format(val))
        return val


class List(Column):

    def validate(self, value):
        val = super(List, self).validate(value)
        if val is None:
            return None  # required = False
        if not isinstance(val, (list, tuple)):
            raise ValidationError('{} is not a valid list'.format(val))
        return val
