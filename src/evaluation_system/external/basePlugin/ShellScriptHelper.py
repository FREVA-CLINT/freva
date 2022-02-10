"""
Created on 27.04.2012

@author: Robert Schuster

Some useful methods to work with shell scripts
"""

import subprocess
import os
from Logger import Logger
import tempfile
import shutil
import atexit
import multiprocessing


class TempDir(object):
    """
    This class represents a temporal directory which is automatically deleted on exit
    """

    def __init__(self, parentdir=None):
        """
        @param parentdir: the directory is created in the parent directory. If the argument
        is none, then the directory is created in the default temp-Directory
        """
        # create the directory
        self.__path = tempfile.mkdtemp(dir=parentdir)

        # register the cleanup-method
        atexit.register(self.cleanup)

    def cleanup(self):
        """
        Remove the temporal directory and its content.
        This method is automatically called on exit
        """
        # check is the directory is still there
        if not os.path.exists(self.__path):
            return

        # delete the directory
        shutil.rmtree(self.__path)

    def getPath(self):
        """
        get the path of the temporal directory
        """
        return self.__path


class ShellScript(object):
    """
    This Class represents a shell script or any other external program
    """

    # the default environment variables
    default_env = os.environ

    @classmethod
    def addDefaultEnvironmentVariable(cls, varname, varvalue):
        """
        Add Environment Variables that are forwarded to every process
        """
        cls.default_env[varname] = varvalue

    @classmethod
    def getstatusoutput(cls, cmd, workpath=None):
        """Return (status, output, cmd) of executing cmd in a shell."""
        """This new implementation should work on all platforms."""
        pipe = subprocess.Popen(
            cmd,
            shell=True,
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=cls.default_env,
            cwd=workpath,
        )
        try:
            output = str.join("", pipe.stdout.readlines())
            sts = pipe.wait()
        except KeyboardInterrupt:
            Logger.Error("process killed by KeyboardInterrupt!")
            pipe.kill()
        if sts is None:
            sts = 0
        return sts, output, cmd

    @classmethod
    def run_scripts_parallel(cls, scripts, nproc=None):
        """
        Run multiple scripts in parallel
        @param scrpits  list object containing ShellScript objects
        @param nproc    number of parallel processes, None=Number of available cpus
        """
        if nproc is None:
            nproc = min(multiprocessing.cpu_count(), len(scripts))
        # create the multiprocessing pool
        pool = multiprocessing.Pool(nproc)
        exitcodes = []
        try:
            res = pool.map_async(_run_script, scripts, callback=exitcodes.append)
            res.get()
        except KeyboardInterrupt:
            Logger.Error("Execution canceled by user!", -1)
            pool.terminate()
        # close the pool again and wait for all processes
        pool.close()
        pool.join()
        return exitcodes[0]

    def checkout(self, output, err_text, err_code, print_without_error=True):
        """
        check the output of getstatusoutput for errors.
        """
        if print_without_error:
            print(output[1])
        if output[0] != 0:
            Logger.Error(err_text)
            Logger.Error(self.getCommand(), errorcode=err_code)

    def __init__(self, scriptfile, workpath=None, check=True):
        """
        create the ShellScript object and check the existence of the script file
        """
        self.scriptfile = scriptfile
        self.arguments = []
        self.workpath = workpath

        # check the existence of the script file
        if (
            check
            and workpath is None
            and not os.path.exists(self.scriptfile)
            or workpath is not None
            and not os.path.exists(workpath + "/" + self.scriptfile)
        ):
            Logger.Error("Script " + self.scriptfile + " not found!")
            exit()

    def addPositionalArgument(self, argument):
        """
        add a positional argument to the script
        """
        self.arguments.append((None, argument))

    def addFlag(self, flag, value=None):
        """
        add a non positional argument with a flag to the program
        """
        self.arguments.append((flag, value))

    def __getArgValueString(self, argument):
        """
        @return: A string representation of the argument
        """
        result = ""
        # call the method recursive if a list is found
        if isinstance(argument, list):
            for x in range(len(argument)):
                result += self.__getArgValueString(argument[x])
                if x < len(argument) - 1:
                    result += " "
        # string type
        elif isinstance(argument, str):
            if (
                " " in argument
                or "?" in argument
                or "(" in argument
                or ")" in argument
                or "'" in argument
            ):
                result += "'" + argument + "'"
            else:
                result += argument
        # integer of float
        elif isinstance(argument, int) or isinstance(argument, float):
            result += str(argument)
        # temporal directory
        elif isinstance(argument, TempDir):
            result += "'" + argument.getPath() + "'"
        elif argument is None:
            pass
        # unsupported argument
        else:
            Logger.Error(
                "ShellScripthelper, __getArgValueString: unsupported argument type "
                + str(type(argument))
            )
        return result

    def run(self):
        """
        Run the Script.
        @return: a tuple with the return value
        """

        # run the script
        return self.getstatusoutput(self.getCommand(), self.workpath)

    def getCommand(self):
        """
        returns the command together with its arguments
        """
        # create a list with arguments
        args = ""
        # loop over all arguments
        for argn in self.arguments:
            if argn[0] is None:
                args += " " + self.__getArgValueString(argn[1])
            else:
                args += " " + argn[0] + " " + self.__getArgValueString(argn[1])

        return self.scriptfile + args


# a module method is needed for parallel execution
def _run_script(script):
    return script.run()
