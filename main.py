from argparse import ArgumentParser
from util import script
from webobj import Route, Server, File
import time
import sys

def main():
    parser = ArgumentParser(description='Logcat.')
    parser.add_argument('module')
    parser.add_argument('--addr', default='localhost:8080')

    args = parser.parse_args(sys.argv[1:])
    module = __import__(args.module)
    addr_parts = args.addr.split(':')
    host = addr_parts[0]
    if len(addr_parts) == 1:
        port = 80
    else:
        port = int(addr_parts[1])
    addr = (host, port)

    server = Server(module.routes, getattr(module, 'authenticator', None), addr)
    server.start()

script()
