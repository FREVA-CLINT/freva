'''
Created on 06.11.2012

@author: estani
'''
import sqlite3
from datetime import datetime, timedelta
import json
import ast
import logging
log = logging.getLogger(__name__)

#Store sqlite3 file and pool
_connection_pool = {}

class HistoryEntry(object):
    def __init__(self, row):
        self.rowid = row[0]
        self.timestamp = row[1]
        self.tool_name = row[2]
        self.version = ast.literal_eval(row[3])
        self.configuration = json.loads(row[4])
        
    def __eq__(self, hist_entry):
        if isinstance(hist_entry, HistoryEntry):
            return self.rowid == hist_entry.rowid and self.timestamp == hist_entry.timestamp and \
                    self.tool_name == hist_entry.tool_name and self.version == hist_entry.version and \
                    self.configuration == hist_entry.configuration
    def __str__(self, compact=True):
        if compact:
            conf_str = str(self.configuration)
            if len(conf_str) > 50:
                conf_str = conf_str[:48] + '...'
            version = '' 
        else:
            conf_str = '\n' + json.dumps(self.configuration, sort_keys=True, indent=2)
            version = ' v%s.%s.%s' % self.version
            
        
        return '%s) %s%s %s' % (self.rowid, self.tool_name, version, conf_str)
        
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
        self._db_file = user.getUserConfigDir(create=True) + '/history.sql3'
        self.initialize()
    
    def _getConnection(self):
        #trying to avoid holding a lock to the DB for too long
        if self._db_file != ':memory:':
            if self._db_file not in _connection_pool:
                _connection_pool[self._db_file] = sqlite3.connect(self._db_file, isolation_level=None)
            return _connection_pool[self._db_file]
        return sqlite3.connect(self._db_file)
    
    def initialize(self, tool_name=None):
        """If not already initialized it will performed the required actions
        There might be diferences as how tools are initialized (maybe multiple DBs/tables)
        so if given, the initialization from a specific tool will be handled."""
        if not self.isInitialized():
            self._getConnection().execute('CREATE TABLE meta(table_name text, version int);')
            self._getConnection().execute('CREATE TABLE history(timestamp text, tool text, version text, configuration text);')
            self._getConnection().execute("INSERT INTO meta VALUES('history', 1);")
    
    def isInitialized(self):
        """If this DB is initialized"""
        try:
            self._getConnection().execute("SELECT * from history limit 1;")
            return True
        except:
            return False
        
    def storeHistory(self, tool, config_dict):
        """Store an analysis run"""
        row = (datetime.now(), 
                tool.__class__.__name__.lower(),    #for case insensitive search 
                repr(tool.__version__), 
                json.dumps(config_dict))
        log.debug('Row: %s', row)
        self._getConnection().execute("INSERT INTO history VALUES(?, ?, ?, ?);", row)
        
    def getHistory(self, tool_name=None, limit=-1, days_span=None, entry_ids=None):
        """Returns the stored history (run analysis) for the given tool.
        Parameters
        tool_name : string
            name of the tool for which the information will be gathered (if None, then everything is returned)
        limit : int
            Amount of rows to be returned (if -1, return all)
        days_span: number or iterable with two values
            return entries located at [from, to] days ago. if only one value it's assumed [days_span, now].
            Days might be floats.
        entry_ids: list of ints or int 
            list of ids to be selected
        @return: list of tuples [(row_id, timestamp, tool_name, version, configuration)]"""
        #ast.literal_eval(node_or_string)
        sql_params = []
        sql_str = "SELECT rowid, * FROM history"
        if tool_name or days_span or entry_ids:
            sql_str = '%s WHERE 1=1' % sql_str
            if entry_ids is not None:
                if isinstance(entry_ids, int): entry_ids=[entry_ids]
                sql_str = '%s AND rowid in (?)' % sql_str
                sql_params.append(','.join(map(str,entry_ids)))
            if tool_name is not None:
                sql_str = '%s AND tool=?' % sql_str
                sql_params.append(tool_name.lower())    #make search case insensitive
            if days_span is not None:
                if isinstance(days_span, (int, float)):
                    #one single span means "from"
                    sql_str = '%s AND timestamp > ?' % sql_str
                    sql_params.append(datetime.now() - timedelta(days=abs(days_span)))
                else:
                    sql_str = '%s AND timestamp > ? AND timestamp < ?' % sql_str
                    sql_params.append(datetime.now() - timedelta(days=abs(days_span[0])))
                    sql_params.append(datetime.now() - timedelta(days=abs(days_span[1])))
                    
        sql_str = sql_str + ' ORDER BY timestamp DESC'
        if limit > 0:
            sql_str = '%s LIMIT ?' % sql_str
            sql_params.append(limit)
             
        log.debug('sql: %s - (%s)', sql_str, tuple(sql_params))
        res = self._getConnection().execute(sql_str, sql_params).fetchall()
        return [HistoryEntry(row) for row in res]
    
        