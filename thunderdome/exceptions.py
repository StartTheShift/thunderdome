#thunderdome exceptions
class ThunderdomeException(Exception): pass
class ModelException(ThunderdomeException): pass
class ValidationError(ThunderdomeException): pass
class DoesNotExist(ThunderdomeException): pass
class MultipleObjectsReturned(ThunderdomeException): pass
class WrongElementType(ThunderdomeException): pass

