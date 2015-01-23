import execjs
from copy import copy
from os import environ
from os.path import abspath, dirname, join

NODE_PATH = abspath(join(dirname(__file__), 'node_modules'))


class LessError(Exception):
    def __init__(self, json_error):
        self.line = json_error['line']
        self.column = json_error['column']
        self.filename = json_error['filename']
        self.error_type = json_error['type']
        self.message = json_error['message']

    def __repr__(self):
        return "<{} {} {}:{}.{}  {}>".format(self.__class__.__name__, self.error_type, self.filename, self.line, self.column, self.message)

    def __str__(self):
        return repr(self)


def render(less_filename, rootpath=None):
    nodejs = execjs.get('Node')
    nodejs.env = copy(environ)
    nodejs.env['NODE_PATH'] = NODE_PATH
    context = nodejs.compile("less = require('less');")
    if rootpath is None:
        rootpath = dirname(less_filename)
    try:
        with open(less_filename) as f:
            data = f.read()
            return context.call_async('less.render', data, {'filename': less_filename, 'rootpath': rootpath}, execjs.callback, this='less')
    except execjs.ProgramError as e:
        raise LessError(e.args[0])


if __name__ == '__main__':
    import sys
    try:
        print(render(sys.argv[1])['css'])
    except LessError as e:
        print(e)
