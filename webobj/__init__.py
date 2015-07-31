import http.server
import json
import socketserver
from collections import namedtuple
import threading
import inspect
import sys
import socket
import time
import traceback
import urllib.parse
import os.path
import subprocess
import functools
import re

from . import jsx
from . import less


def parse_path(path):
    unquoted = urllib.parse.unquote(path)
    parts = [x for x in unquoted.split('/') if x != '']
    new = []
    for p in parts:
        if (p == '..'):
            if len(new):
                new.pop()
            else:
                raise Exception()
        else:
            new.append(p)
    return '/' + '/'.join(new)


# Arbitrarily use 2KiB as max request line size.
MAX_REQUEST_LINE = 2048

LOG_PREFIX = '\U0001f310 '
PILE_OF_POO = '\U0001f4a9'
FIRE = '\U0001f525'
RED = '\x1b[31m'
GREEN = '\x1b[32m'
NORMAL = '\x1b[39m'

DEFAULT_ADDR = ('localhost', 8080)


auto = object()

class Created(Exception):
    def __init__(self, resource_id):
        super().__init__()
        self.resource_id = resource_id


def webmethod(fn):
    fn.is_webmethod = True
    return fn



def first_matching(check, lst):
    return next(filter(check, lst))


class NewWebObject:
    def check_match(self, path, method):
        return None


class Route(namedtuple('Route', ['route', 'content'])):
    def matches(self, path, method):
        if path == self.route:
            return self.content, None
        if path.startswith(self.route):
            if hasattr(self.content, 'check_match'):
                content = self.content.check_match(path[len(self.route):], method)
                if content is not None:
                    return content, None
        return None, None


class RegExpRoute(namedtuple('Route', ['route', 'content'])):
    def matches(self, path, method):
        match = re.match(self.route, path)
        if match is None:
            return None, None

        if hasattr(self.content, 'check_match'):
            content = self.content.check_match(path[len(self.route):], method)
        else:
            content = self.content

        return content, match.groups()


class Function:
    def __init__(self, fn, content_type=None):
        self.fn = fn
        self.content_type = content_type

    @property
    def data(self):
        return self.fn()


_JsonFunction = namedtuple('_JsonFunction', 'fn')


class JsonGetFunction(_JsonFunction):
    pass


class JsonPostFunction(_JsonFunction):
    pass


class JsonPutFunction(_JsonFunction):
    pass


class Data:
    def __init__(self, data, content_type=None):
        self.data = data
        self.content_type = content_type


class File:
    def __init__(self, filename, content_type=auto):
        self.filename = filename
        if content_type is auto:
            # guess from filename
            if filename.endswith('.js'):
                self.content_type = 'application/javascript'
            elif filename.endswith('.css'):
                self.content_type = 'text/css'
            elif filename.endswith('.png'):
                self.content_type = 'image/png'
            elif filename.endswith('.html'):
                self.content_type = 'text/html'
            elif filename.endswith('.woff'):
                self.content_type = 'application/x-font-woff'
            else:
                self.content_type = None
        else:
            self.content_type = content_type

    @property
    def data(self):
        with open(self.filename, 'rb') as f:
            return f.read()


class Dir:
    def __init__(self, dir_path):
        self.dir_path = dir_path

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.dir_path)

    def check_match(self, path):
        assert not path.startswith('/')
        assert '../' not in path
        full_path = os.path.join(self.dir_path, path)
        if os.path.exists(full_path):
            return File(full_path)
        else:
            return None


class Jsx:
    def __init__(self, jsx_filename):
        self.jsx_filename = jsx_filename
        self.content_type = 'application/javascript'

    @property
    def data(self):
        return jsx.transform(self.jsx_filename).encode('utf8')

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.jsx_filename)


class Babel:
    def __init__(self, babel_filename):
        self.babel_filename = babel_filename
        self.content_type = 'application/javascript'

    @property
    def data(self):
        return subprocess.check_output(["babel", self.babel_filename, "--source-maps-inline"])

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.babel_filename)


class Less:
    def __init__(self, less_filename):
        self.less_filename = less_filename
        self.content_type = 'text/css'

    @property
    def data(self):
        return less.render(self.less_filename)['css'].encode('utf8')

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.less_filename)


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


class Handler(http.server.BaseHTTPRequestHandler):
    routes = property(lambda self: self.server.routes)

    def time_string(self):
        """Return the current time formatted for logging."""
        time_with_us = time.time()
        us = (time_with_us % 1.0) * 1000000
        _, _, _, hh, mm, ss, _, _, _ = time.localtime(time_with_us)
        return "%02d:%02d:%02d.%06d" % (hh, mm, ss, us)

    def do_error(self, status):
        self.send_response(status)
        self.end_headers()
        self.wfile.write('<html>Error: {}</html>'.format(status).encode())

    def log_message(self, fmt, *args):
        sys.stderr.write(LOG_PREFIX + "[{}] {}\n".format(self.time_string(), fmt % args))

    def log_request(self, code=999):
        if code < 300:
            color = GREEN
        else:
            color = RED
        self.log_message('{}%3d{} %s %s'.format(color, NORMAL), code, self.command, self.path)

    def handle_one_request(self):
        """Handle a single HTTP request.

        """
        try:
            self.raw_requestline = self.rfile.readline(MAX_REQUEST_LINE + 1)

            if len(self.raw_requestline) > MAX_REQUEST_LINE:
                # Exceed max request line size. Return 414 error.
                self.close_connection = 1
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(414)
                return

            if len(self.raw_requestline) == 0:
                # No data read, just close the connection
                self.close_connection = 1
                return

            if not self.parse_request():
                # An error code has been sent, just exit
                return

            try:
                self.do_request()
            except Exception as e:
                msg = "{}999{} {} {}\n                    {}   {}{}{}"
                self.log_error(msg.format(RED, NORMAL, self.command, self.path, FIRE, RED, e, NORMAL))
                self.close_connection = 1
                traceback.print_exc()
                return
            # actually send the response if not already done.
            self.wfile.flush()

        except socket.timeout as e:
            # a read or a write timed out.  Discard this connection
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1
            return

    def do_request(self):
        if self.command in ('POST', 'PUT'):
            content_length = int(self.headers['Content-Length'])
            data = self.rfile.read(content_length)

        parsed_path = parse_path(self.path)
        try:
            content, extra = first_matching(lambda x: x[0] is not None, (x.matches(parsed_path, self.command) for x in self.routes))
        except StopIteration:
            self.do_error(404)
            return

        authorization_header = self.headers.get('Authorization')
        if self.server.authenticator is not None:
            account = self.server.authenticator.get_account(authorization_header)
        else:
            account = None

        if self.command == 'POST':
            try:
                post_args = json.loads(data.decode())
            except ValueError:
                self.do_error(400)
                return

        if isinstance(content, (Data, File, Function, Babel, Jsx, Less)):
            if self.command == 'GET':
                self.send_response(200)
                if content.content_type is not None:
                    self.send_header("Content-type", content.content_type)
                self.end_headers()
                self.wfile.write(content.data)
            else:
                self.send_error(501, "Unsupported method (%r)" % self.command)

        # I don't particular like the implementation of
        # Json{Get|Post|Put}Function.  It will almost certainly
        # required a refactor at some point soon.
        elif isinstance(content, JsonGetFunction):
            if self.command == 'GET':
                self.send_response(200)
                self.send_header("Content-type", 'application/json')
                self.end_headers()
                if extra is None:
                    fn = content.fn
                else:
                    fn = functools.partial(content.fn, *extra)
                data = fn()
                self.wfile.write(json.dumps(data).encode('utf8'))
            else:
                self.send_error(501, "Unsupported method (%r)" % self.command)

        elif isinstance(content, JsonPostFunction):
            if self.command == 'POST':
                if extra is None:
                    fn = content.fn
                else:
                    fn = functools.partial(content.fn, *extra)
                code, result = fn(post_args)
                self.send_response(code)
                self.send_header("Content-type", 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode('utf8'))
            else:
                self.send_error(501, "Unsupported method (%r)" % self.command)

        elif isinstance(content, JsonPutFunction):
            if self.command == 'PUT':
                put_data = json.loads(data.decode())
                if extra is None:
                    fn = content.fn
                else:
                    fn = functools.partial(content.fn, *extra)
                response = fn(put_data)
                if response is None:
                    response = 201
                self.send_response(response)
                self.end_headers()
            else:
                self.send_error(501, "Unsupported method (%r)" % self.command)

        elif isinstance(content, NewWebObject):
            if self.command == 'GET':
                self.send_response(200)
                self.send_header("Content-type", 'application/json')
                self.end_headers()
                self.wfile.write(content.web_data)

            elif self.command == 'POST':
                # FIXME: handle case when no actions specified
                action = post_args['action']
                args = post_args['args']
                action_method = getattr(content, action)
                try:
                    result = action_method(**args)
                except Created as e:
                    self.send_response(201)
                    loc_uri = self.path + "/" + e.resource_id
                    self.send_header("Location", loc_uri)
                    self.end_headers()
                    return

                self.send_response(200)
                self.send_header("Content-type", 'application/json')
                self.end_headers()

                self.wfile.write(json.dumps(result).encode('utf8'))
                return
            else:
                self.send_error(501, "Unsupported method (%r)" % self.command)

        else:
            # I'm not 100% happy with this approach for for now it will work
            if self.command == 'PUT':
                content.handle_put(data)
                self.send_response(200)
                self.end_headers()

            elif self.command == 'DELETE':
                content.handle_delete()
                self.send_response(200)
                self.end_headers()

            else:
                self.send_error(501, "Unsupported method (%r)" % self.command)


class Server:
    def __init__(self, routes, authenticator=None, addr=DEFAULT_ADDR):
        self.routes = routes
        self.authenticator = authenticator
        self.addr = addr

    def start(self):
        self.server = ThreadedServer(self.addr, Handler)
        self.server.routes = self.routes
        self.server.authenticator = self.authenticator
        self.server.serve_forever()
