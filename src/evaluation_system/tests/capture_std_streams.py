'''
Created on 02.11.2012

@author: estani

Utils for testing
'''
import sys
from StringIO import StringIO


class OutputWrapper(object):
    def __init__(self, ioStream):
        self.__buffer = StringIO()
        self.__original = ioStream
        self.capturing = False
        
    def write(self, s):
        if self.capturing: self.__buffer.write(s)
        self.__original.write(s)
        
    def writelines(self, strs):
        if self.capturing: self.__buffer.writelines(strs)
        self.__original.writelines( strs)
        
    def getvalue(self):
        return self.__buffer.getvalue()
    
    def reset(self):
        self.__buffer.truncate(0)
        
    def getOriginalStream(self):
        return self.__original
    
    def startCapturing(self):
        self.capturing = True
        
    def stopCapturing(self):
        self.capturing = False
    
    def __getattr__(self, *args, **kwargs):
        return self.__original.__getattribute__(*args, **kwargs)
    
__original_stdout = sys.stdout
__original_stderr = sys.stderr
    

#overwrite the stadard out
sys.stdout = OutputWrapper(sys.stdout)
sys.stderr = OutputWrapper(sys.stderr)

#this will get exported
stdout = sys.stdout
stderr = sys.stderr 
