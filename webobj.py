import http.server
import json
import socketserver
from collections import namedtuple
import threading
import inspect
import sys
import socket


LOG_PREFIX = '\U0001f310 '

DEFAULT_ADDR = ('localhost', 8080)


auto = object()


def first_matching(check, lst):
    return next(filter(check, lst))


class EventStream(threading.Condition):
    def __init__(self, web_object):
        self.web_object = web_object
        lock = threading.Lock()
        super().__init__(lock)


class WebObject:
    web_fields = []

    def __setattr__(self, name, value):
        if name not in self.web_fields:
            object.__setattr__(self, name, value)
            return

        self.event_stream.acquire()
        object.__setattr__(self, name, value)
        self.event_stream.notify_all()
        self.event_stream.release()

    @property
    def web_state(self):
        return {fld: getattr(self, fld) for fld in self.web_fields}

    @property
    def web_data(self):
        return json.dumps(self.web_state).encode('utf8')

    @property
    def event_stream(self):
        try:
            es = self._event_steam
        except AttributeError:
            es = EventStream(self)
            self._event_steam = es

        return es


class Route(namedtuple('Route', ['route', 'content'])):
    def matches(self, request):
        return request.path == self.route


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
            elif filename.endswith('.html'):
                self.content_type = 'text/html'
            else:
                self.content_type = None
        else:
            self.content_type = content_type

    @property
    def data(self):
        with open(self.filename, 'rb') as f:
            return f.read()


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


class Handler(http.server.BaseHTTPRequestHandler):
    routes = property(lambda self: self.server.routes)

    def do_error(self, status):
        self.send_response(status)
        self.end_headers()
        self.wfile.write('<html>Error: {}</html>'.format(status).encode())

    def log_message(self, fmt, *args):
        sys.stderr.write(LOG_PREFIX + "{} - - [{}] {}\n".format(self.address_string(), self.log_date_time_string(), fmt % args))

    def handle_one_request(self):
        """Handle a single HTTP request.

        """
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(414)
                return
            if not self.raw_requestline:
                self.close_connection = 1
                return
            if not self.parse_request():
                # An error code has been sent, just exit
                return
            mname = 'do_' + self.command
            if not hasattr(self, mname):
                self.send_error(501, "Unsupported method (%r)" % self.command)
                return
            method = getattr(self, mname)
            try:
                method()
            except Exception as e:
                self.log_error("Error occured during request: {} {}: {}".format(self.command, self.path, e))
                self.close_connection = 1
                return
            # actually send the response if not already done.
            self.wfile.flush()
        except socket.timeout as e:
            # a read or a write timed out.  Discard this connection
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1
            return

    def do_GET(self):
        try:
            route = first_matching(lambda x: x.matches(self), self.routes)
        except StopIteration:
            self.do_error(404)
            return

        content = route.content

        if isinstance(content, (Data, File)):
            self.send_response(200)
            if content.content_type is not None:
                self.send_header("Content-type", content.content_type)
            self.end_headers()
            self.wfile.write(content.data)
        elif isinstance(content, WebObject):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(content.web_data)
        elif isinstance(content, EventStream):
            self.send_response(200)
            self.send_header("Content-type", "text/event-stream")
            self.end_headers()
            content.acquire()
            while True:
                json_data = json.dumps(content.web_object.web_state)
                data = 'data: {}\n\n'.format(json_data)
                try:
                    self.wfile.write(data.encode('utf-8'))
                    self.wfile.flush()
                except:
                    content.release()
                    break
                content.wait()
        else:
            raise Exception("unhandled content: {}".format(content))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        data = self.rfile.read(content_length)

        try:
            route = first_matching(lambda x: x.matches(self), self.routes)
        except StopIteration:
            self.do_error(404)
            return

        try:
            post_args = json.loads(data.decode())
        except ValueError:
            self.do_error(400)
            return

        content = route.content

        if inspect.ismethod(content):
            result = content(**post_args)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({'result': result}).encode('utf=8'))


class Server:
    def __init__(self, routes, addr=DEFAULT_ADDR):
        self.routes = routes
        self.addr = addr

    def start(self):
        self.server = ThreadedServer(self.addr, Handler)
        self.server.routes = self.routes
        self.server.serve_forever()
