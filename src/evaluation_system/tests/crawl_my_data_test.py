"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import os
import unittest
import logging
import sys
import pytest

from evaluation_system.tests import similar_string


def test_auto_doc(stdout, prog_name):
    from evaluation_system.commands.crawl_my_data import Command
    sys.stdout = stdout
    dummy_cmd = Command()
    stdout.startCapturing()
    stdout.reset()
    with pytest.raises(SystemExit):
        dummy_cmd.run(['--help'])
    stdout.stopCapturing()
    doc_str = stdout.getvalue()
    target_str = f'''Use this command to update your projectdata.

Usage: {prog_name} [options]

Options:
-d, --debug  turn on debugging info and show stack trace on exceptions.
-h, --help   show this help message and exit
--path=PATH  crawl the given directory
'''
    assert similar_string(doc_str, target_str) is True

def test_crawl_my_data(stdout, dummy_settings):
    from evaluation_system.commands.crawl_my_data import Command
    sys.stdout = stdout
    dummy_cmd = Command()
    stdout.startCapturing()
    stdout.reset()
    dummy_cmd.run([])
    stdout.stopCapturing()
    output = stdout.getvalue()
    assert 'Please wait while the system is crawling your data' in output
    assert 'Finished' in output
    assert 'Crawling took' in output

    with pytest.raises(SystemExit):
        pytest.raises(dummy_cmd.run(['--path=/tmp/forbidden/folder']))
