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
def async_exec(command, stdoutCallback):
    fork = yield from asyncio.create_subprocess_shell(
        (command),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    tasks = []
    if fork.stdout is not None:
        tasks.append(read_stdout(fork.stdout, stdoutCallback))
    else:
        print('No stdout')

    yield from asyncio.wait(tasks)

    retCode = yield from fork.wait()

    return retCode


def test_callback(line):
    print("Received: '%s'"%line)


loop = asyncio.get_event_loop()

tasks = []
for command in sys.argv[1:]:
    task = async_exec(command, test_callback)
    tasks.append(task)

loop.run_until_complete(asyncio.wait(tasks))

# Test with
# PATH=$PWD/../bde-tools/bin:$PATH python3 ~/PycharmProjects/python_experiments/checkout.py \
# "export WAFLOCK=.waf-lock-dbg_exc_mt BDE_WAF_UFID=dbg_exc_mt; waf configure build --target=bsl" \
# "export WAFLOCK=.waf-lock-opt_exc_mt BDE_WAF_UFID=opt_exc_mt; waf configure build --target=bsl"

