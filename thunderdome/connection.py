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
import socket
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

    def __init__(self, message, full_response={}):
        """
        Initialize the thunderdome query error message.

        :param message: The message text itself
        :type message: str
        :param full_response: The full query response
        :type full_response: dict
        
        """
        super(ThunderdomeQueryError, self).__init__(message)
        self._full_response = full_response

    @property
    def raw_response(self):
        """
        Return the raw query response.

        :rtype: dict
        
        """
        return self._full_response


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
_statsd = None


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

        
def setup(hosts, graph_name, username=None, password=None, index_all_fields=False, statsd=None):
    """
    Records the hosts and connects to one of them.

    :param hosts: list of hosts, strings in the <hostname>:<port> or just <hostname> format
    :type hosts: list of str
    :param graph_name: The name of the graph as defined in the rexster.xml
    :type graph_name: str
    :param username: The username for the rexster server
    :type username: str
    :param password: The password for the rexster server
    :type password: str
    :param index_all_fields: Toggle automatic indexing of all vertex fields
    :type index_all_fields: boolean
    :param statsd: host:port or just host of statsd server to report metrics to
    :type statsd: str
    :rtype None
    """
    global _hosts
    global _graph_name
    global _username
    global _password
    global _index_all_fields
    global _statsd

    _graph_name = graph_name
    _username = username
    _password = password
    _index_all_fields = index_all_fields


    if statsd:
        try:
            sd = statsd
            import statsd
            tmp = sd.split(':')
            if len(tmp) == 1:
                tmp.append('8125')
            _statsd = statsd.StatsClient(tmp[0], int(tmp[1]), prefix='thunderdome')
        except ImportError:
            logging.warning("Statsd configured but not installed.  Please install the statsd package.")
        except:
            raise

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
    
    create_unique_index('vid', 'String')

    #index any models that have already been defined
    from thunderdome.models import vertex_types
    for klass in vertex_types.values():
        klass._create_indices()
    
    
def execute_query(query, params={}, transaction=True, context=""):
    """
    Execute a raw Gremlin query with the given parameters passed in.

    :param query: The Gremlin query to be executed
    :type query: str
    :param params: Parameters to the Gremlin query
    :type params: dict
    :param context: String context data to include with the query for stats logging
    :rtype: dict
    
    """
    if transaction:
        query = "g.stopTransaction(FAILURE)\n" + query

    # If we have no hosts available raise an exception
    if len(_hosts) <= 0:
        raise ThunderdomeConnectionError('Attempt to execute query before calling thunderdome.connection.setup')
    
    host = _hosts[0]
    #url = 'http://{}/graphs/{}/tp/gremlin'.format(host.name, _graph_name)
    data = json.dumps({'script':query, 'params': params})
    headers = {'Content-Type':'application/json', 'Accept':'application/json', 'Accept-Charset':'utf-8'}
    import time
    try:
        start_time = time.time()
        conn = httplib.HTTPConnection(host.name, host.port)
        conn.request("POST", '/graphs/{}/tp/gremlin'.format(_graph_name), data, headers)
        response = conn.getresponse()
        content = response.read()

        total_time = int((time.time() - start_time) * 1000)

        if context and _statsd:
            _statsd.timing("{}.timer".format(context), total_time)
            _statsd.incr("{}.counter".format(context))


    except socket.error as sock_err:
        if _statsd:
            total_time = int((time.time() - start_time) * 1000)
            _statsd.incr("thunderdome.socket_error".format(context), total_time)
        raise ThunderdomeQueryError('Socket error during query - {}'.format(sock_err))
    except:
        raise
    
    logger.info(json.dumps(data))
    logger.info(content)

    try:
        response_data = json.loads(content)
    except ValueError as ve:
        raise ThunderdomeQueryError('Loading Rexster results failed: "{}"'.format(ve))
    
    if response.status != 200:
        if 'message' in response_data and len(response_data['message']) > 0:
            graph_missing_re = r"Graph \[(.*)\] could not be found"
            if re.search(graph_missing_re, response_data['message']):
                raise ThunderdomeGraphMissingError(response_data['message'])
            else:
                raise ThunderdomeQueryError(
                    response_data['message'],
                    response_data
                )
        else:
            if _statsd:
                _statsd.incr("{}.error".format(context))
            raise ThunderdomeQueryError(
                response_data['error'],
                response_data
            )

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
