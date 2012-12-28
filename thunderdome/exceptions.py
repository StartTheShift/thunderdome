#thunderdome exceptions
class ThunderdomeException(BaseException): pass
class ModelException(ThunderdomeException): pass
class ValidationError(ThunderdomeException): pass
class DoesNotExist(ThunderdomeException): pass
class MultipleObjectsReturned(ThunderdomeException): pass

