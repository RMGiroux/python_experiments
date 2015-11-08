__author__ = 'RMGiroux'

import asyncio
from asyncio import subprocess
import sys

class OutputCollector:
    def __init__(self, name):
        self.name = name

    @asyncio.coroutine
    def process_line(self, stream):
        while not stream.at_eof():
            line = yield from stream.readline()
            print("%s: %s"%(name, line))


@asyncio.coroutine
def read_stdout(stream, callback):
    while True:
        line = yield from stream.readline()
        print('received', repr(line))
        if not line:
            break
        else:
            callback(line)

@asyncio.coroutine
def async_exec(repo, stdoutCallback):
    fork = yield from asyncio.create_subprocess_shell(
        ("git clone %s"%repo),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    tasks = []
    if fork.stdout is not None:
        tasks.append(read_stdout(fork.stdout, stdoutCallback))
    else:
        print('No stdout')

    yield from asyncio.wait(tasks)

    retCode = yield from fork.wait()

    return retCode


def test_callback(line):
    print("Received: %s"%line)


loop = asyncio.get_event_loop()

task = async_exec(sys.argv[1], test_callback)
loop.run_until_complete(task)