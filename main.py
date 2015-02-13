from util import script
from webobj import Route, Server, File
import time
import sys

def main():
    module = __import__(sys.argv[1])
    server = Server(module.routes, getattr(module, 'authenticator', None))
    server.start()

script()
