"""
Created on 20.04.2012

@author: Robert Schuster
"""
from Logger import Logger
from ShellScriptHelper import ShellScript


class NCLscript(ShellScript):
    """
    This class represents an ncl script together with all its arguments
    """

    def addArgument(self, argument, value):
        """
        Add an argument to the script
        @param argument: name of the argument
        @param value: value of the argument
        """
        # check the argument
        if not isinstance(argument, str):
            Logger.Error("NCLhelper, addArgument: the argument name must be a string!")
            return
        self.arguments.append((argument, value))

    def __getArgValueString(self, argument):
        """
        @return: A string representation of the argument
        """
        result = ""
        # call the method recursive if a list is found
        if isinstance(argument, list):
            result += "(/"
            for x in range(len(argument)):
                result += self.__getArgValueString(argument[x])
                if x < len(argument) - 1:
                    result += ","
            result += "/)"
        # string type
        elif isinstance(argument, str):
            result += '"' + argument + '"'
        # integer of float
        elif isinstance(argument, int) or isinstance(argument, float):
            result += str(argument)
        # unsupported argument
        else:
            Logger.Error(
                "NCLhelper, __getArgValueString: unsupported argument type "
                + str(type(argument))
            )
        return result

    def getCommand(self):
        """
        returns the command together with its arguments
        """
        # create a list with arguments
        args = ""
        # loop over all arguments
        for argn in self.arguments:
            args += " '"
            args += argn[0] + "=" + self.__getArgValueString(argn[1])
            args += "'"
        return "ncl -Q %s%s" % (self.scriptfile, args)

    def run(self):
        """
        Run the Script.
        @return: a tuple with the return value
        """
        # run the script
        result = self.getstatusoutput(self.getCommand(), self.workpath)
        if result[0] == 0 and "fatal:" in result[1]:
            result = 1, result[1], result[2]
        if "warning" in result[1]:
            print(result[1])
        if "debug" in result[1]:
            print(result[1])
        return result
