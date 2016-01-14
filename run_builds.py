#!/usr/bin/env python3

__author__ = 'RMGiroux'

debug_mode = 0

import asyncio
from asyncio import subprocess
from datetime import datetime, timedelta
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
            print("%s: %s" % (self.name, line))


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
    fork = yield from asyncio.create_subprocess_shell((command),
                                                      stdout=subprocess.PIPE,
                                                      stderr=subprocess.STDOUT)

    tasks = []
    if fork.stdout is not None:
        tasks.append(read_stdout(fork.stdout, stdoutCallback))
    else:
        print('No stdout')

    yield from asyncio.wait(tasks)

    retCode = yield from fork.wait()

    return retCode


def run_waf(directory, ufid, target=None):
    prefix = "%s/_build/%s" % (directory, ufid)
    waflock = ".waf-lock-%s" % ufid
    build_dir = "_build/%s" % (ufid)

    environment = (
        "export PREFIX=%s WAFLOCK=%s BDE_WAF_UFID=%s BDE_WAF_BUILD_DIR=%s" % (
            prefix, waflock, ufid, build_dir))

    waf_command = "waf configure clean build --test=run -j6 -k"

    if target is not None:
        waf_command += (" --target=%s" % target)

    command = "%s; cd %s; %s 2>&1 | tee %s.out " % (
        environment, directory, waf_command, ufid)

    # with term.location(1, 30 + (position * 5)):
    #    print("Starting command %s"%command)

    line_proc = LineProcessor(ufid, "uplid-placeholder")

    task = async_exec(command, lambda x: line_proc.line_callback(x))

    return task


progress_regex_string = b"\[\s*(\d+)/\s*(\d+)\s*\] \w+\s+(.*)"
progress_regex = re.compile(progress_regex_string)

test_summary = b"Test Summary"
test_summary_regex = re.compile(test_summary)

test_pass = b"All tests passed."
test_pass_regex = re.compile(test_pass)

test_fail = b"tests have fail"
test_fail_regex = re.compile(test_fail)

class LineProcessor:
    position = 1

    block_start_pattern_string = b"\\[(\\S+) \\((WARNING|ERROR|TEST)\\)\\] <<<<<<<<<<"
    block_end_pattern_string = b">>>>>>>>>>"
    block_pattern_string = block_start_pattern_string + b"(.*?)" + block_end_pattern_string

    block_start_pattern = re.compile(block_start_pattern_string)
    # re.S is aka re.DOTALL, so "." matches newlines as well.
    block_pattern = re.compile(block_pattern_string, re.S)
    block_end_pattern = re.compile(block_end_pattern_string)

    def __init__(self, ufid, uplid):
        self.ufid = ufid
        self.uplid = uplid
        self.position = LineProcessor.position
        self.start_time = datetime.now()

        LineProcessor.position = LineProcessor.position + 1

        self.diagnostic_buffer = ""
        self.processing_diag   = False

    def line_callback(self, line):
        line = line.rstrip()

        if debug_mode:
            with term.location(1, 30 + self.position * 2):
                print(" " * 80)
            with term.location(1, 30 + self.position * 2):
                print("%-20s: %-50s" % (self.ufid, line.decode("ascii")[-50:]))

        match = progress_regex.search(line)
        if match is not None:
            with term.location(1, self.position * 2):
                print(format_meter(int(match.group(1)), int(match.group(2)),
                                   (datetime.now() - self.start_time).total_seconds(),
                                   ascii=True, prefix=("%-20s" % self.ufid)))
            with term.location(5, self.position * 2 + 1):
                print("%60s" % match.group(3).decode("ascii")[-60:])

            return  # RETURN

        if self.processing_diag:
            match = LineProcessor.block_end_pattern.search(line)
            if match is not None:
                self.diagnostic_buffer+=line
                # TODO: Hand off diagnostic to database
                with term.location(1, 50):
                    print(" " * 80)
                with term.location(1, 50):
                    print(self.diagnostic_buffer[0:60])

                self.processing_diag = False
                return

            self.diagnostic_buffer+=line
            return

        match = LineProcessor.block_start_pattern.search(line)
        if match is not None:
            self.processing_diag = True
            self.diagnostic_buffer = line

            self.diagnostic_component = match.group(1)
            self.diagnostic_type = match.group(2)

            return

        match = test_summary_regex.search(line)
        if match is not None:
            with term.location(5, self.position * 2 + 1):
                print("%60s" % " ")
            with term.location(5, self.position * 2 + 1):
                print("%-60s" % line.decode("ascii")[-60:])

            if debug_mode:
                with term.location(1, 40 + self.position * 3):
                    print("%-20s: Test summary matched" % self.ufid)

                with term.location(1, 50):
                    print(
                            "%-20s: test summary match - hit enter to continue" % self.ufid)

                    my_input = sys.stdin.readline()

            return  # RETURN

        match = test_pass_regex.search(line)
        if match is not None:
            with term.location(5, self.position * 2 + 1):
                print("[%-60s]" % term.green(line.decode("ascii")[-60:]))

            if debug_mode:
                with term.location(1, 41 + self.position * 3):
                    print("%-20s: Test pass regex matched" % self.ufid)

                with term.location(1, 50):
                    print(
                            "%-20s: test pass    match - hit enter to continue" % self.ufid)

                    my_input = sys.stdin.readline()

            return  # RETURN

        match = test_fail_regex.search(line)
        if match is not None:
            with term.location(5, self.position * 2 + 1):
                print("[%-60s]" % term.red(line.decode("ascii")[-60:]))

            if debug_mode:
                with term.location(1, 42 + self.position * 3):
                    print("%-20s: Test fail regex matched" % self.ufid)

                with term.location(1, 50):
                    print(
                            "%-20s: test fail    match - hit enter to continue" % self.ufid)

                    my_input = sys.stdin.readline()

            return  # RETURN


loop = asyncio.get_event_loop()

checkout_path = sys.argv[1]

tasks = []
tasks.append(run_waf(checkout_path, "opt_exc_mt", target="bsls"))
tasks.append(
        run_waf(checkout_path, "dbg_exc_mt_64", target="bslscm"))
tasks.append(
        run_waf(checkout_path, "dbg_exc_mt_cpp11", target="bsls"))


print(term.clear())

with term.location(1, (LineProcessor.position + 2) * 2):
    with term.hidden_cursor():
        try:
            loop.run_until_complete(asyncio.wait(tasks))
        except e:
            print("Failed with exception:")
            print(e)

        loop.close()

print(term.move(1,50))

if debug_mode:
    print("Hit enter to exit")

    my_input = sys.stdin.readline()


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
