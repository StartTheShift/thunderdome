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

import collections
import pyparsing
import re


# Cache of parsed files
_parsed_file_cache = {}


class GroovyFunctionParser(object):
    """
    Given a string containing a single function definition this class will 
    parse the function definition and return information regarding it.
    """

    # Simple Groovy sub-grammar definitions
    KeywordDef  = pyparsing.Keyword('def')
    VarName     = pyparsing.Regex(r'[A-Za-z_]\w*')
    FuncName    = VarName
    FuncDefn    = KeywordDef + FuncName + "(" + pyparsing.delimitedList(VarName) + ")" + "{"
    
    # Result named tuple
    GroovyFunction = collections.namedtuple('GroovyFunction', ['name', 'args', 'body', 'defn'])
    
    @classmethod
    def parse(cls, data):
        """
        Parse the given function definition and return information regarding
        the contained definition.
        
        :param data: The function definition in a string
        :type data: str
        :rtype: dict
        
        """
        try:
            # Parse the function here
            result = cls.FuncDefn.parseString(data)
            result_list = result.asList()
            args = result_list[3:result_list.index(')')]
            # Return single line or multi-line function body
            fn_body = re.sub(r'[^\{]+\{', '', data, count=1)
            parts = fn_body.strip().split('\n')
            fn_body = '\n'.join(parts[0:-1])
            return cls.GroovyFunction(result[1], args, fn_body, data)
        except Exception, ex:
            return {}
        

def parse(file):
    """
    Parse Groovy code in the given file and return a list of information about
    each function necessary for usage in queries to database.
    
    :param file: The file containing groovy code.
    :type file: str
    :rtype: 
    
    """
    # Check cache before parsing file
    global _parsed_file_cache
    if file in _parsed_file_cache:
        return _parsed_file_cache[file]
    
    FuncDefnRegexp = r'^def.*\{'
    FuncEndRegexp = r'^\}.*$'
    with open(file, 'r') as f:
        data = f.read()
    file_lines = data.split("\n")
    all_fns = []
    fn_lines = ''
    for line in file_lines:
        if len(fn_lines) > 0:
            if re.match(FuncEndRegexp, line):
                fn_lines += line + "\n"
                all_fns.append(fn_lines)
                fn_lines = ''
            else:
                fn_lines += line + "\n"
        elif re.match(FuncDefnRegexp, line):
            fn_lines += line + "\n"
            
    func_results = []
    for fn in all_fns:
        func_results += [GroovyFunctionParser.parse(fn)]
        
    _parsed_file_cache[file] = func_results
    return func_results
