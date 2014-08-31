import http.server
import json
import socketserver
from collections import namedtuple
import threading
import inspect


DEFAULT_ADDR = ('localhost', 8080)


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
    def __init__(self, data):
        self.data = data


class File:
    def __init__(self, filename):
        self.filename = filename

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

    def do_GET(self):
        try:
            route = first_matching(lambda x: x.matches(self), self.routes)
        except StopIteration:
            self.do_error(404)
            return

        content = route.content

        if isinstance(content, (Data, File)):
            self.send_response(200)
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
