#!/usr/bin/env python3

from webobj import Server, Route, Data


def main(args):
    routes = [
        Route('/', Data('<html>Hello, Flub</html>')),
    ]
    server = Server(routes)
    server.start()


if __name__ == '__main__':
    import sys
    main(sys.argv)
