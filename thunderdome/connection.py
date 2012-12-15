#http://pypi.python.org/pypi/cql/1.0.4
#http://code.google.com/a/apache-extras.org/p/cassandra-dbapi2 /
#http://cassandra.apache.org/doc/cql/CQL.html

from collections import namedtuple
import json
import logging
import Queue
import random
import requests

from thunderdome.exceptions import ThunderdomeException

logger = logging.getLogger(__name__)

class ThunderdomeConnectionError(ThunderdomeException): pass
class ThunderdomeQueryError(ThunderdomeException): pass

Host = namedtuple('Host', ['name', 'port'])
_hosts = []
_host_idx = 0
_graph_name = None
_username = None
_password = None

def setup(hosts, graph_name, username=None, password=None):
    """
    Records the hosts and connects to one of them

    :param hosts: list of hosts, strings in the <hostname>:<port>, or just <hostname>
    """
    global _hosts
    global _graph_name
    global _username
    global _password
    _graph_name = graph_name
    _username = username
    _password = password
    
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
    
    results = execute_query('g.getIndexedKeys(Vertex.class)')
    import ipdb; ipdb.set_trace()
    for idx in ['vid', 'element_type']:
        if idx not in results:
            execute_query("g.createKeyIndex(keyname, Vertex.class)", {'keyname':idx})
    
    
def execute_query(query, params={}):
    host = _hosts[0]
    url = 'http://{}:{}/graphs/{}/tp/gremlin'.format(host.name, host.port, _graph_name)
    query = 'g.stopTransaction(SUCCESS);' + query
    data = json.dumps({'script':query, 'params': params})
    headers = {'Content-Type':'application/json', 'Accept':'application/json'}
    response = requests.post(url, data=data, headers=headers)
    
    logger.info(response.request.data)
    logger.info(response.content)
    
    if response.status_code != 200:
        raise ThunderdomeQueryError(response.content)
    return response.json['results']



