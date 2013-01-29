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

from collections import namedtuple
import httplib
import json
import logging
import Queue
import random
import re
import textwrap

from thunderdome.exceptions import ThunderdomeException
from thunderdome.spec import Spec


logger = logging.getLogger(__name__)


class ThunderdomeConnectionError(ThunderdomeException):
    """
    Problem connecting to Rexster
    """


class ThunderdomeQueryError(ThunderdomeException):
    """
    Problem with a Gremlin query to Titan
    """


class ThunderdomeGraphMissingError(ThunderdomeException):
    """
    Graph with specified name does not exist
    """


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
    """
    Execute a raw Gremlin query with the given parameters passed in.

    :param query: The Gremlin query to be executed
    :type query: str
    :param params: Parameters to the Gremlin query
    :type params: dict
    :rtype: dict
    
    """
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
        if 'message' in response_data and len(response_data['message']) > 0:
            graph_missing_re = r"Graph \[(.*)\] could not be found"
            if re.search(graph_missing_re, response_data['message']):
                raise ThunderdomeGraphMissingError(response_data['message'])
            else:
                raise ThunderdomeQueryError(response_data['message'])
        else:
            raise ThunderdomeQueryError(response_data['error'])

    return response_data['results'] 


def sync_spec(filename, host, graph_name, dry_run=False):
    """
    Sync the given spec file to thunderdome.

    :param filename: The filename of the spec file
    :type filename: str
    :param host: The host the be synced
    :type host: str
    :param graph_name: The name of the graph to be synced
    :type graph_name: str
    :param dry_run: Only prints generated Gremlin if True
    :type dry_run: boolean
    
    """
    Spec(filename).sync(host, graph_name, dry_run=dry_run)
