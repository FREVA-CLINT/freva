#!/usr/bin/env python3

from pathlib import Path
import subprocess as sub
import shlex
import sys


class Plugin:
    result=''
    def __init__(self, cmd):
        
        self.runTool({'cmd': cmd})
          
    @staticmethod
    def _execute(cmd):
        res = sub.Popen(cmd, stdout=sub.PIPE, universal_newlines=True)
        for stdout_line in iter(res.stdout.readline, ""):
            yield stdout_line
        res.stdout.close()
        return_code = res.wait()
        if return_code:
            raise sub.CalledProcessError(return_code, cmd)


    def runTool(self, config_dict=None):
       
        self.call(f'{config_dict["cmd"]}')
        #return self.result 

    def call(self, cmd, verbose=True, return_stdout=True):

        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        #cmd.append('&')
        out = ''
        for line in self._execute(cmd):
            if verbose:
                print(line, end='', flush=True)
            out += line
        if return_stdout:
            return out





