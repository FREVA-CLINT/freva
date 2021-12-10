import sys
import shlex
from subprocess import run, PIPE
from difflib import SequenceMatcher


def run_cli(cmd):
    from freva.cli import main as main_cli
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    return main_cli(cmd)

def run_command_with_capture(cmd, stdout, args_list=[], stderr=None, attr='run'):
    sys.stdout = stdout
    stdout.startCapturing()
    stdout.reset()
    getattr(cmd, attr)(args_list)
    stdout.stopCapturing()
    res = stdout.getvalue()
    return res

def similar_string(a, b, thresh=0.98):
    a = a.strip().replace('\n', ' ').replace('\t', ' ').replace('  ', ' ').strip()
    b = b.strip().replace('\n', ' ').replace('\t', ' ').replace('  ', ' ' ).strip()
    print('a', a.split(' '))
    print('\n')
    print('b', b.split(' '))
    ratio = SequenceMatcher(None, a, b).ratio()
    print(ratio)
    return ratio >= thresh
