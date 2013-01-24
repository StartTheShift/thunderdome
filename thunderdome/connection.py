#http://pypi.python.org/pypi/cql/1.0.4
#http://code.google.com/a/apache-extras.org/p/cassandra-dbapi2 /
#http://cassandra.apache.org/doc/cql/CQL.html

from collections import namedtuple
import httplib
import json
import logging
import Queue
import random
import textwrap

from thunderdome.exceptions import ThunderdomeException
from thunderdome.spec import Spec

logger = logging.getLogger(__name__)

class ThunderdomeConnectionError(ThunderdomeException): pass
class ThunderdomeQueryError(ThunderdomeException): pass

Host = namedtuple('Host', ['name', 'port'])
_hosts = []
_host_idx = 0
_graph_name = None
_username = None
_password = None
_index_all_fields = True
_existing_indices = None

def create_key_index(name):
    """
    Creates a key index if it does not already exist
    """
    global _existing_indices
    _existing_indices = _existing_indices or execute_query('g.getIndexedKeys(Vertex.class)')
    if name not in _existing_indices:
        execute_query(
            "g.createKeyIndex(keyname, Vertex.class); g.stopTransaction(SUCCESS)",
            {'keyname':name}, transaction=False)
        _existing_indices = None

def create_unique_index(name, data_type):
    """
    Creates a key index if it does not already exist
    """
    global _existing_indices
    _existing_indices = _existing_indices or execute_query('g.getIndexedKeys(Vertex.class)')
    
    if name not in _existing_indices:
        execute_query(
            "g.makeType().name(name).dataType({}.class).functional().unique().indexed().makePropertyKey(); g.stopTransaction(SUCCESS)".format(data_type),
            {'name':name}, transaction=False)
        _existing_indices = None
        
def setup(hosts, graph_name, username=None, password=None, index_all_fields=True):
    """
    Records the hosts and connects to one of them.

    :param hosts: list of hosts, strings in the <hostname>:<port> or just <hostname> format
    :type hosts: str
    :param graph_name: The name of the graph as defined in the rexster.xml
    :type graph_name: str
    :param username: The username for the rexster server
    :type username: str
    :param password: The password for the rexster server
    :type password: str
    :param index_all_fields: Toggle automatic indexing of all vertex fields
    :type index_all_fields: boolean

    """
    global _hosts
    global _graph_name
    global _username
    global _password
    global _index_all_fields
    _graph_name = graph_name
    _username = username
    _password = password
    _index_all_fields = index_all_fields
    
    for host in hosts:
        host = host.strip()
        host = host.split(':')
        if len(host) == 1:
            _hosts.append(Host(host[0], 8182))
        elif len(host) == 2:
            _hosts.append(Host(*host))
        else:
            raise ThunderdomeConnectionError("Can't parse {}".format(''.join(host)))

    if not _hosts:
        raise ThunderdomeConnectionError("At least one host required")

    random.shuffle(_hosts)
    
    create_key_index('element_type')
    create_unique_index('vid', 'String')

    #index any models that have already been defined
    from thunderdome.models import vertex_types
    for klass in vertex_types.values():
        klass._create_indices()
    
    
def execute_query(query, params={}, transaction=True):
    if transaction:
        query = 'g.stopTransaction(FAILURE)\n' + query

    host = _hosts[0]
    #url = 'http://{}/graphs/{}/tp/gremlin'.format(host.name, _graph_name)
    data = json.dumps({'script':query, 'params': params})
    headers = {'Content-Type':'application/json', 'Accept':'application/json'}

    conn = httplib.HTTPConnection(host.name, host.port)
    conn.request("POST", '/graphs/{}/tp/gremlin'.format(_graph_name), data, headers)
    response = conn.getresponse()
    content = response.read()

    
    logger.info(json.dumps(data))
    logger.info(content)

    response_data = json.loads(content)
    
    if response.status != 200:
        raise ThunderdomeQueryError(response_data['error'])

    return response_data['results'] 


def sync_spec(filename, host, graph_name):
    """
    Sync the given spec file to thunderdome.

    :param filename: The filename of the spec file
    :type filename: str
    :param host: The host the be synced
    :type host: str
    :param graph_name: The name of the graph to be synced
    :type graph_name: str
    
    """
    Spec(filename).sync(host, graph_name)
