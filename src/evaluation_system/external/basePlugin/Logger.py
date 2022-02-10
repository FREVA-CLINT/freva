"""
Created on 17.04.2012

@author: Robert Schuster
"""

import subprocess


class Logger(object):
    """
    The logger class provides static methodes to print colored text.
    """

    # the info should not be colored by default
    color_info = None
    color_error = "red"
    cols = None

    @classmethod
    def Error(cls, text, errorcode=0):
        """
        Print the text in red on the screen with the prefix ERROR:"
        Set the error code to something different from zero to terminate the program
        """
        print(cls.colored("ERROR: " + text, cls.color_error))
        if errorcode != 0:
            exit(errorcode)

    @classmethod
    def Info(cls, text, color=None):
        """
        Print the text in orange on the screen with the prefix INFO:"
        """
        if color is None:
            color = cls.color_info
        if text.startswith("\n"):
            print("")
            cls.Info(text[1:], color)
            return
        print(cls.colored("INFO: " + text, color))

    @classmethod
    def Warning(cls, text):
        """
        Print the text in orange on the screen with the prefix WARNING:"
        """
        print(cls.colored("WARNING: " + text, cls.color_info))

    @classmethod
    def InfoStr(cls, text, prefix=True):
        """
        Returns an info-str as printed by the Info method
        """
        if prefix:
            return cls.colored("INFO: " + text, cls.color_info)
        else:
            return cls.colored(text, cls.color_info)

    @classmethod
    def colored(cls, text, color):
        if color == "orange":
            text = "\033[93m" + text + "\033[0m"
        if color == "green":
            text = "\033[92m" + text + "\033[0m"
        if color == "red":
            text = "\033[91m" + text + "\033[0m"
        return text

    @classmethod
    def Indent(cls, text, nspace_first, nspace_following=None):
        """
        print a text indented and add line breaks at the terminal width
        """
        if nspace_following is None:
            nspace_following = nspace_first

        # split into single lines
        if text.startswith("\n"):
            print("")
            cls.Indent(text[1:], nspace_first, nspace_following)
            return
        lines = text.splitlines()
        if len(lines) > 1:
            cls.Indent(lines[0], nspace_first, nspace_following)
            for i in range(1, len(lines)):
                cls.Indent(lines[i], nspace_following)
            return

        # try to get the terminal size
        if cls.cols is None:
            pipe = subprocess.Popen(
                "stty size",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            output = str.join("", pipe.stdout.readlines())
            code = pipe.wait()
            if code == 0:
                cls.rows, cls.cols = map(lambda x: int(x), output.split())
            else:
                cls.cols = 0

        # how many space is available?
        avcols = cls.cols - nspace_first
        # terminal is to small?
        if avcols < 10 or len(text) <= avcols:
            print("%s%s" % (" " * nspace_first, text))
        else:
            print("%s%s" % (" " * nspace_first, text[0:avcols]))
            cls.Indent(text[avcols:], nspace_following)
