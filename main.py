import os
from util import script
from webobj import Route, Server, File
import time
import sys

def main():
    sys.path = [os.getcwd()] + sys.path
    module = __import__(sys.argv[1])
    server = Server(module.routes, module.authenticator)
    server.start()

script()
