#!/usr/bin/env python3

import signal
import sys
import time
from util import simplecontextmanager
import termios
import os
from copy import copy

# Lightning bolt
PREFIX = "\u26A1 "

running = True
last_ctrl_c = 0
child_pid = None
child_died = False
got_sigint = False
killing_child = False

# Python3.2 and earlier doesn't support the InterruptedError
try:
    interrupted_exception = InterruptedError
except NameError:
    interrupted_exception = ()


def sigint_handler(signal, frame):
    global last_ctrl_c, running, got_sigint
    os.write(2, (PREFIX + "<sigint>\n").encode('utf8'))
    got_sigint = True
    interrupt_time = time.time()
    if interrupt_time - last_ctrl_c < 0.5:
        running = False
    last_ctrl_c = interrupt_time


def sigchld_handler(signal, frame):
    global child_died, killing_child
    if not killing_child:
        os.write(2, (PREFIX + "<sigchld>\n").encode('utf8'))
    child_died = True


@simplecontextmanager
def change_termios(fd):
    new = before = termios.tcgetattr(fd)
    new[3] &= ~termios.ECHOCTL
    termios.tcsetattr(fd, termios.TCSAFLUSH, before)
    yield
    termios.tcsetattr(fd, termios.TCSAFLUSH, before)

def load():
    global child_pid
    assert child_pid is None
    print(PREFIX + "Loading application")
    pid = os.fork()
    if pid == 0:
        env = copy(os.environ)
        os.execv(sys.executable, ['python3', '-m', 'main'] + sys.argv[1:])
        print(PREFIX + "exec failed.")
        sys.exit()
    else:
        child_pid = pid

def stop():
    global child_pid, child_died, got_sigint, killing_child
    print_reason = True
    if not child_died:
        print_reason = False
        killing_child = True
        os.kill(child_pid, signal.SIGTERM)
        # Wait until the child dies (or we exit anyway)
        while not child_died:
            signal.pause()
        child_died = False
        killing_child = False

    assert child_pid is not None
    while True:
        try:
            pid, reason = os.waitpid(child_pid, 0)
            break
        except interrupted_exception as e:
            pass
    assert pid == child_pid
    if print_reason:
        if os.WIFEXITED(reason):
            print(PREFIX + "server exit: {}".format(os.WEXITSTATUS(reason)))
        elif os.WIFSIGNALED(reason):
            print(PREFIX + "server killed: {}".format(os.WTERMSIG(reason)))
        else:
            print(PREFIX + "served died: <unknown>")

    child_pid = None

    while not got_sigint:
        signal.pause()
    got_sigint = False


def main():
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGCHLD, sigchld_handler)
    with change_termios(sys.stdin.fileno()):
        # Just watch and wait!
        while running:
            load()
            signal.pause()
            stop()
    print(PREFIX + "<exiting>")


assert __name__ == '__main__'
main()
