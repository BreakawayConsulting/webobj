import http.server
import socketserver
from collections import namedtuple


DEFAULT_ADDR = ('localhost', 8080)


class Route(namedtuple('Route', ['route', 'content'])):
    pass


class Data:
    def __init__(self, data):
        self.data = data


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


class Handler(http.server.BaseHTTPRequestHandler):
    pass


class Server:
    def __init__(self, routes, addr=DEFAULT_ADDR):
        self.routes = routes
        self.addr = addr

    def start(self):
        self.server = ThreadedServer(self.addr, Handler)
        self.server.serve_forever()
