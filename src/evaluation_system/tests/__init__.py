from difflib import SequenceMatcher
import mock
import os
import sys
import shlex
from subprocess import run, PIPE


def mockenv(**envvars):
    return mock.patch.dict(os.environ, envvars)


def run_cli(cmd):
    from freva.cli import main as main_cli

    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    return main_cli(cmd)


def similar_string(a, b, thresh=0.98):
    a = a.strip().replace("\n", " ").replace("\t", " ").replace("  ", " ").strip()
    b = b.strip().replace("\n", " ").replace("\t", " ").replace("  ", " ").strip()
    print("a", a)
    print("\n")
    print("b", b)
    ratio = SequenceMatcher(None, a, b).ratio()
    print(ratio >= thresh, thresh)
    return ratio >= thresh
