#!/usr/bin/env python3

import time
import threading
from webobj import Server, Route, Data, WebObject

class Flub(WebObject):
    web_fields = ['bar']

    def __init__(self):
        self.bar = 1

    def run(self):
        while True:
            time.sleep(1)
            self.bar += 1


def main(args):
    flub = Flub()
    flub_thread = threading.Thread(target=flub.run)
    flub_thread.start()

    routes = [
        Route('/', Data(b'<html>Hello, Flub</html>')),
        Route('/flub', flub),
    ]
    server = Server(routes)
    server.start()


if __name__ == '__main__':
    import sys
    main(sys.argv)
