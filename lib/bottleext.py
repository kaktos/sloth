import bottle

from bottle import request, response, route, Jinja2Template
from bottle import install, uninstall

from json import dumps as json_dumps

###############################################################################
#                      fix  bottle return json                               #
###############################################################################

class JSONAPIPlugin(object):
    name = 'jsonapi'
    api  = 2

    def __init__(self, json_dumps=json_dumps):
        uninstall('json')
        self.json_dumps = json_dumps

    def apply(self, callback, context):
        dumps = self.json_dumps
        if not dumps: return callback
        def wrapper(*a, **ka):
            rv = callback(*a, **ka)
            if isinstance(rv, dict) or isinstance(rv, list):
                #Attempt to serialize, raises exception on failure
                json_response = dumps(rv)
                #Set content type only if serialization succesful
                response.content_type = 'application/json'
                return json_response
            return rv
        return wrapper


###############################################################################
#                      fix  bottle jinja2 template                            #
###############################################################################
class MyJinja2Template(Jinja2Template):
    def prepare(self, filters=None, tests=None, globals = None, **kwargs):
        from jinja2 import Environment, FunctionLoader
        if 'prefix' in kwargs: # TODO: to be removed after a while
            raise RuntimeError('The keyword argument `prefix` has been removed. '
                'Use the full jinja2 environment name line_statement_prefix instead.')
        self.env = Environment(loader=FunctionLoader(self.loader), **kwargs)
        if filters: self.env.filters.update(filters)
        if tests: self.env.tests.update(tests)
        if globals: self.env.globals.update(globals)
        if self.source:
            self.tpl = self.env.from_string(self.source)
        else:
            self.tpl = self.env.get_template(self.filename)


       