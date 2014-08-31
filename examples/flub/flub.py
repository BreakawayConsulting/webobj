#!/usr/bin/env python3

import os
import time
import threading
from webobj import Server, Route, Data, WebObject, File

BASE_DIR = os.path.dirname(__file__)

def rel_path(*parts):
    return os.path.join(BASE_DIR, *parts)


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
        Route('/', File(rel_path('index.html'))),
        Route('/flub', flub),
        Route('/flub+events', flub.event_stream),
    ]
    server = Server(routes)
    server.start()


if __name__ == '__main__':
    import sys
    main(sys.argv)
