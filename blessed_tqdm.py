__author__ = 'RMGiroux'

from tqdm import format_meter
from blessings import Terminal
from time import sleep

term = Terminal()

"""
    A simple experiment to see if TQDM (great progress bars!) and blessings
    (great terminal location and colour control)
"""
for i in range(10):
    with term.location(1,1):
        print(term.red+term.on_black, format_meter(i, 9, 0.3*i))
        sleep(0.3)


