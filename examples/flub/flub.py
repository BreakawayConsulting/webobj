#!/usr/bin/env python3

import os
import time
import threading
from webobj import Server, RegExpRoute, Route, Data, NewWebObject, \
    File, JsonPostFunction, JsonGetFunction, JsonPutFunction

BASE_DIR = os.path.dirname(__file__)

def rel_path(*parts):
    return os.path.join(BASE_DIR, *parts)


class Flub(NewWebObject):
    web_fields = ['bar']

    def __init__(self):
        self.running = True
        self.bar = 1

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        while True:
            time.sleep(1)
            if self.running:
                self.bar += 1


def json_get_example():
    return {'example': 5}


def json_post_example(data):
    print("JSON POST:", data)
    return 201, {'example': 6}


def json_put_example(data):
    print("JSON PUT:", data)


def json_get_regexp_example(id1, id2):
    print("JSON GET:", id1, id2)
    return {'example': 5}


def json_post_regexp_example(id1, id2, data):
    print("JSON POST:", id1, id2, data)
    return 200, {'example': 6}


def json_put_regexp_example(id1, id2, data):
    print("JSON PUT:", id1, id2, data)


def main(args):
    flub = Flub()
    flub_thread = threading.Thread(target=flub.run)
    flub_thread.start()

    routes = [
        Route('/', File(rel_path('index.html'))),
        Route('/flub.js', File(rel_path('flub.js'))),
        Route('/react.js', File(rel_path('react.js'))),
        Route('/flub', flub),
        Route('/flub/start', flub.start),
        Route('/flub/stop', flub.stop),
        Route('/flub/json_get', JsonGetFunction(json_get_example)),
        Route('/flub/json_post', JsonPostFunction(json_post_example)),
        Route('/flub/json_put', JsonPutFunction(json_put_example)),
        RegExpRoute(r'/flub/(.*)/(.*)/json_get$', JsonGetFunction(json_get_regexp_example)),
        RegExpRoute(r'/flub/(.*)/(.*)/json_post$', JsonPostFunction(json_post_regexp_example)),
        RegExpRoute(r'/flub/(.*)/(.*)/json_put$', JsonPutFunction(json_put_regexp_example)),
    ]
    server = Server(routes)
    server.start()


if __name__ == '__main__':
    import sys
    main(sys.argv)
