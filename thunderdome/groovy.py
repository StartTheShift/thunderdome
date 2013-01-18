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
