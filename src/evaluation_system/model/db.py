'''
Created on 06.11.2012

@author: estani
'''

class UserDB(object):
    '''
    Encapsulates access to the local DB.
    The main idea is to have a DB for storing the analysis runs.
    This might evolve from a simple parameter call + timestamp to storing the whole configuration.
    This class will jusp provide the methods for handling this action, the action itself must be
    implemented from within the tool.
    '''


    def __init__(self, user):
        '''
        As it is related to a user the user should be known at construction time
        '''
        self._user = user
        
    def initialize(self, tool=None):
        """If not already initialized it will performed the required actions
        There might be diferences as how tools are initialized (maybe multiple DBs/tables)
        so if given, the initialization from a specific tool will be handled."""
        pass
    
    
        