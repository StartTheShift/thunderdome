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

class Row(object):
    def __init__(self, data):
        for k,v in data.iteritems():
            setattr(self, k, v)
    
class Table(object):
    """
    A table accepts the results of a GremlinMethod in it's
    constructor.  
    It can be iterated over like a normal list, but within the rows
    the dictionaries are accessible via .notation
    
    For example:
    
    # returns a table of people & my friend edge to them
    # the edge contains my nickname for that person
    friends = thunderdome.GremlinMethod()
    
    def get_friends_and_my_nickname(self):
        result = self.friends()
        result = Table(result)
        for i in result:
            print "{}:{}".format(i.friend_edge.nickname, i.person.name)
    """
    
    def __init__(self, gremlin_result):
        self._gremlin_result = gremlin_result
        self._position = 0
        
    
    def __getitem__(self, key): 
        """
        returns an enhanced dictionary
        """
        return Row(self._gremlin_result[key])
        
    def __iter__(self):
        return self
    
    def next(self):
        if self._position == len(self._gremlin_result):
            self._position = 0
            raise StopIteration()
        tmp = self._gremlin_result[self._position]
        self._position += 1
        return Row(tmp)
    
    
    def __len__(self):
        return len(self._gremlin_result)
