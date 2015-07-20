"""Collection of useful utilities.

  From: https://github.com/bennoleslie/pyutil.
"""
import inspect
import sys
import contextlib
from functools import wraps


class SysExit(Exception):
    def __init__(self, code, msg=None):
        super().__init__()
        self.code = code
        self.msg = msg


def script():
    s = inspect.stack()[1][0]
    caller_name = s.f_locals['__name__']
    if caller_name != '__main__':
        return

    caller_main = s.f_locals.get('main')
    if caller_main is None:
        print("main() not found.", file=sys.stderr)
        sys.exit(1)
    try:
        sys.exit(caller_main())
    except SysExit as e:
        if e.msg:
            print(e.msg, file=sys.stderr)
        sys.exit(e.code)
    except KeyboardInterrupt:
        # FIXME: This could probably be handled
        # better to match the Ctrl-C signal exit
        # code
        sys.exit(1)


class _GeneratorSimpleContextManager(contextlib._GeneratorContextManager):
    """Helper for @simplecontextmanager decorator."""

    def __exit__(self, type, value, traceback):
        if type is None:
            try:
                next(self.gen)
            except StopIteration:
                return
            else:
                raise RuntimeError("generator didn't stop")
        else:
            if value is None:
                # Need to force instantiation so we can reliably
                # tell if we get the same exception back
                value = type()

            try:
                next(self.gen)
            except StopIteration as exc:
                # Suppress the exception *unless* it's the same exception that
                # was passed to throw().  This prevents a StopIteration
                # raised inside the "with" statement from being suppressed
                return exc is not value
            else:
                raise RuntimeError("generator didn't stop")
            finally:
                return False


def simplecontextmanager(func):
    """@simplecontextmanager decorator.

    Typical usage:

        @simplecontextmanager
        def some_generator(<arguments>):
            <setup>
            yield <value>
            <cleanup>

    This makes this:

        with some_generator(<arguments>) as <variable>:
            <body>

    equivalent to this:

        <setup>
        try:
            <variable> = <value>
            <body>
        finally:
            <cleanup>

    """
    @wraps(func)
    def helper(*args, **kwds):
        return _GeneratorSimpleContextManager(func, *args, **kwds)
    return helper
