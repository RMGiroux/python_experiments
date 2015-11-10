__author__ = 'RMGiroux'

import asyncio
from asyncio import subprocess

import sys

import re

from pylibinit import addlibpath
addlibpath.add_lib_path()

from blessings import Terminal
from tqdm import format_meter

term = Terminal()

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

def run_waf(directory, ufid, position):
    prefix="%s/_build/%s"%(directory, ufid)
    waflock=".waf-lock-%s"%ufid
    build_dir="_build/%s"%(ufid)

    environment="export PREFIX=%s WAFLOCK=%s BDE_WAF_UFID=%s BDE_WAF_BUILD_DIR=%s"%(prefix,waflock,ufid,build_dir)

    command="%s; cd %s; waf configure clean build --test=run -j6 -k 2>&1 | tee %s.out "%(environment, directory, ufid)

    #with term.location(1, 30 + (position * 5)):
    #    print("Starting command %s"%command)

    task=async_exec(command,
                    lambda x: test_callback(position, ufid, x))

    return task


regex=b"\[\s*(\d+)/\s*(\d+)\s*\] \w+\s+(.*)"
progress_regex=re.compile(regex)
#print("Regex is: ", regex)

def test_callback(position, ufid, line):
    match = progress_regex.match(line)
    if match is not None:
        with term.location(1, position * 2):
            print(format_meter(int(match.group(1)),
                               int(match.group(2)),
                               0,
                               prefix = ("%-20s"%ufid)),
                   " %50s" % match.group(3).decode("utf-8")[-50:])


loop = asyncio.get_event_loop()

checkout_path = sys.argv[1]

tasks = []
position = 1
tasks.append(run_waf(checkout_path, "opt_exc_mt", position))
position += 1
tasks.append(run_waf(checkout_path, "dbg_exc_mt_64", position))
position += 1
tasks.append(run_waf(checkout_path, "dbg_exc_mt_cpp11", position))
position += 1

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
