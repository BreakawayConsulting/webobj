import http.server
import json
import socketserver
from collections import namedtuple
import threading
import inspect
import sys
import jsx
import socket
import less
import time
import traceback

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


# class EventStream(threading.Condition):
#     def __init__(self, web_object):
#         self.web_object = web_object
#         lock = threading.Lock()
#         super().__init__(lock)


class NewWebObject:
    def check_match(self, path):
        return None


# class WebObject:
#     web_fields = []

#     def __setattr__(self, name, value):
#         if name not in self.web_fields:
#             object.__setattr__(self, name, value)
#             return

#         self.event_stream.acquire()
#         object.__setattr__(self, name, value)
#         self.event_stream.notify_all()
#         self.event_stream.release()

#     @property
#     def web_state(self):
#         return {fld: getattr(self, fld) for fld in self.web_fields}

#     @property
#     def web_data(self):
#         return json.dumps(self.web_state).encode('utf8')

#     @property
#     def event_stream(self):
#         try:
#             es = self._event_steam
#         except AttributeError:
#             es = EventStream(self)
#             self._event_steam = es

#         return es


class Route(namedtuple('Route', ['route', 'content'])):
    def matches(self, request):
        if request.path == self.route:
            return self.content
        if request.path.startswith(self.route):
            if isinstance(self.content, NewWebObject):
                content = self.content.check_match(request.path[len(self.route):])
                if content is not None:
                    return content
        return None


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

class Jsx:
    def __init__(self, jsx_filename):
        self.jsx_filename = jsx_filename
        self.content_type = 'application/javascript'

    @property
    def data(self):
        return jsx.transform(self.jsx_filename).encode('utf8')

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.jsx_filename)


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
        if self.command == 'POST':
            content_length = int(self.headers['Content-Length'])
            data = self.rfile.read(content_length)

        try:
            content = first_matching(lambda x: x is not None, (x.matches(self) for x in self.routes))
        except StopIteration:
            self.do_error(404)
            return

        authorization_header = self.headers.get('Authorization')
        account = self.server.authenticator.get_account(authorization_header)

        if self.command == 'POST':
            try:
                post_args = json.loads(data.decode())
            except ValueError:
                self.do_error(400)
                return

        if isinstance(content, (Data, File, Jsx, Less)):
            if self.command == 'GET':
                self.send_response(200)
                if content.content_type is not None:
                    self.send_header("Content-type", content.content_type)
                self.end_headers()
                self.wfile.write(content.data)
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
            raise Exception("unhandled content: {}".format(content))


    # Temp removal of support for WebObject and EventStream
    # def do_GET(self):
    #     elif isinstance(content, WebObject):
    #         self.send_response(200)
    #         self.end_headers()
    #         self.wfile.write(content.web_data)
    #     elif isinstance(content, EventStream):
    #         self.send_response(200)
    #         self.send_header("Content-type", "text/event-stream")
    #         self.end_headers()
    #         content.acquire()
    #         while True:
    #             json_data = json.dumps(content.web_object.web_state)
    #             data = 'data: {}\n\n'.format(json_data)
    #             try:
    #                 self.wfile.write(data.encode('utf-8'))
    #                 self.wfile.flush()
    #             except:
    #                 content.release()
    #                 break
    #             content.wait()

    # Temp removal of support for posting to bare methods
    # if inspect.ismethod(content):
    #     result = content(**post_args)
    #     self.send_response(200)
    #     self.end_headers()
    #     self.wfile.write(json.dumps({'result': result}).encode('utf=8'))


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
