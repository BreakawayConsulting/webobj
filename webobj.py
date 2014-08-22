import http.server
import json
import socketserver
from collections import namedtuple


DEFAULT_ADDR = ('localhost', 8080)


def first_matching(check, lst):
    return next(filter(check, lst))


class WebObject:
    web_fields = []

    @property
    def web_state(self):
        return {fld: getattr(self, fld) for fld in self.web_fields}

    @property
    def web_data(self):
        return json.dumps(self.web_state).encode('utf8')


class Route(namedtuple('Route', ['route', 'content'])):
    def matches(self, request):
        return request.path == self.route


class Data:
    def __init__(self, data):
        self.data = data


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

        if isinstance(content, Data):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(content.data)
        elif isinstance(content, WebObject):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(content.web_data)


class Server:
    def __init__(self, routes, addr=DEFAULT_ADDR):
        self.routes = routes
        self.addr = addr

    def start(self):
        self.server = ThreadedServer(self.addr, Handler)
        self.server.routes = self.routes
        self.server.serve_forever()
