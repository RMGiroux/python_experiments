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

def run_waf(directory, ufid):
    prefix="%s/_build/%s"%(directory, ufid)
    waflock=".waf-lock-%s"%ufid
    build_dir="%s/_build/%s"

    environment="export PREFIX=%s WAFLOCK=%s BDE_WAF_UFID=%s BDE_WAF_BUILD_DIR=%s"%(prefix,waflock,ufid,build_dir)

    command="%s; cd %s; waf configure clean build --test=run -j6 -k"%(environment, directory)

    print("Starting command %s"%command)
    task=async_exec(command,
                    lambda x: test_callback(ufid, x))

    return task


def test_callback(ufid, line):
    print("%12s: '%s'"%(ufid, line))


loop = asyncio.get_event_loop()

tasks = []
tasks.append(run_waf("/home/mgiroux/bde", "opt_exc_mt"))
tasks.append(run_waf("/home/mgiroux/bde", "opt_exc_mt_64"))
tasks.append(run_waf("/home/mgiroux/bde", "dbg_exc_mt"))
tasks.append(run_waf("/home/mgiroux/bde", "dbg_exc_mt_64"))
tasks.append(run_waf("/home/mgiroux/bde", "dbg_exc_mt_cpp11"))

loop.run_until_complete(asyncio.wait(tasks))

# Test with
# PATH=$PWD/../bde-tools/bin:$PATH python3 ~/PycharmProjects/python_experiments/checkout.py \
# "export WAFLOCK=.waf-lock-dbg_exc_mt BDE_WAF_UFID=dbg_exc_mt; waf configure build --target=bsl" \
# "export WAFLOCK=.waf-lock-opt_exc_mt BDE_WAF_UFID=opt_exc_mt; waf configure build --target=bsl"

# Here's what bde_setwafenv.py sets...
# export BDE_WAF_UPLID=unix-linux-x86_64-2.6.18-gcc-4.9.2
# export BDE_WAF_UFID=dbg_exc_mt_64
# export BDE_WAF_BUILD_DIR="_build/unix-linux-x86_64-2.6.18-gcc-4.9.2-dbg_exc_mt_64"
# export WAFLOCK=".lock-waf-unix-linux-x86_64-2.6.18-gcc-4.9.2-dbg_exc_mt_64"
# export CXX=/opt/swt/install/gcc-4.9.2/bin/g++
# export CC=/opt/swt/install/gcc-4.9.2/bin/gcc
# unset BDE_WAF_COMP_FLAGS
# export PREFIX="/home/mgiroux/bde-install/unix-linux-x86_64-2.6.18-gcc-4.9.2-dbg_exc_mt_64"
# export PKG_CONFIG_PATH="/home/mgiroux/bde-install/unix-linux-x86_64-2.6.18-gcc-4.9.2-dbg_exc_mt_64/lib/pkgconfig"
