#thunderdome exceptions
class ThunderdomeException(BaseException): pass
class ModelException(ThunderdomeException): pass
class ValidationError(ThunderdomeException): pass

