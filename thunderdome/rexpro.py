from contextlib import contextmanager

def open_transaction():
    pass

def close_transaction(success=True):
    pass

@contextmanager
def transaction():
    open_transaction()
    yield
    #TODO: catch errors and close transaction
    close_transaction()

def execute_query(query, params):
    pass