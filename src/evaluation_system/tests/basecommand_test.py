from pathlib import Path
import os
import pytest
import sys


from evaluation_system.tests import similar_string

def test_help_command(dummy_cmd, stdout, prog_name):
        sys.stdout = stdout
        stdout.startCapturing()
        stdout.reset()
        with pytest.raises(SystemExit):
            dummy_cmd.run(['--help'])
        doc_str = stdout.getvalue()
        stdout.stopCapturing()
        print(f'doc_str: {doc_str}')

        target_str = f'''This is a test dummy

Usage: {prog_name}  [options]

Options:
  -d, --debug   turn on debugging info and show stack trace on exceptions.
  -h, --help    show this help message and exit
  --input=PATH  Some input value
'''
        assert similar_string(doc_str, target_str, 0.75 ) is True

def test_bad_option(dummy_cmd, stdout):

     sys.stdout = stdout
     stdout.startCapturing()
     stdout.reset()
     with pytest.raises(SystemExit):
         dummy_cmd.run(['--input1'])
     help_out = stdout.getvalue()
     stdout.stopCapturing()
     target_out =  '''no such option: input1\n Did you mean this?\n\tinput'''
     assert similar_string(help_out, target_out, 1) is True

def test_dummy_command(dummy_cmd, stdout):

     sys.stdout = stdout
     stdout.startCapturing()
     stdout.reset()
     dummy_cmd.run(['--input=10', '-d'])
     stdout.stopCapturing()
     command_out = stdout.getvalue()
     assert similar_string(command_out , 'The answer is 10\n') is True

