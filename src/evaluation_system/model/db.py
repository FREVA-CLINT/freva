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
        self.timestamp = row[1] #datetime object
        self.tool_name = row[2]
        self.version = ast.literal_eval(row[3])
        self.configuration = json.loads(row[4])
        self.results = json.loads(row[5]) if row[5] else {}
        
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
            
        
        return '%s) %s%s [%s] %s' % (self.rowid, self.tool_name, version, self.timestamp.strftime('%F %H:%M:%S'), conf_str)
        
class UserDB(object):
    '''
    Encapsulates access to the local DB.
    The main idea is to have a DB for storing the analysis runs.
    This might evolve from a simple parameter call + timestamp to storing the whole configuration.
    This class will jusp provide the methods for handling this action, the action itself must be
    implemented from within the tool.
    '''
    __tables = {'meta': {1:['CREATE TABLE meta(table_name text, version int);',
                            "INSERT INTO meta VALUES('meta', 1);"],
                         2: ['ALTER TABLE meta ADD COLUMN description TEXT;',
                             "INSERT INTO meta VALUES('meta', 2, 'Added description column');"]},    
                'history': {1: ['CREATE TABLE history(timestamp timestamp, tool text, version text, configuration text);',
                                "INSERT INTO meta VALUES('history', 1);"],
                            2: ["ALTER TABLE history ADD COLUMN result text;",
                                "INSERT INTO meta VALUES('history', 2, 'Added ');"]},
                '__order' : [('meta', 1), ('history', 1), ('meta', 2), ('history', 2)]}
    """This data structure is managing the schema Upgrade of the DB.
    The structure is: {<table_name>: {<version_number>:[list of sql cmds required]},...
                        __order: [list of tuples (<tble_name>, <version>) marking the cronological
                                        ordering of updates]"""

    def __init__(self, user):
        '''
        As it is related to a user the user should be known at construction time
        '''
        self._user = user
        self._db_file = user.getUserConfigDir(create=True) + '/history.sql3'
        self.initialize()
    
    def _getConnection(self):
        #trying to avoid holding a lock to the DB for too long
        if self._db_file not in _connection_pool:
            _connection_pool[self._db_file] = sqlite3.connect(self._db_file, isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)
        return _connection_pool[self._db_file]
    
    def initialize(self, tool_name=None):
        """If not already initialized it will performed the required actions
        There might be differences as how tools are initialized (maybe multiple DBs/tables)
        so if given, the initialization from a specific tool will be handled.
        While initializing the schemas will get upgraded."""
        if not self.isInitialized():
            #well we need to walk throw history and replay what's missing. We assume a monotone increasing timeline
            #so when the first missing step is found, it as well as all the remining ones need to be replayed.
            #in order to update this DB state to the latest known one.
            for table_name, version in self.__tables['__order']:
                db_perform_update_step = True
                try:
                    res = self._getConnection().execute('SELECT * FROM meta WHERE table_name = ? AND version = ?', (table_name, version))
                    res = res.fetchone();
                    if res:
                        #the expected state is done, so just skip it 
                        db_perform_update_step = False
                except Exception as e:
                    if table_name == 'meta' and version == 1:
                        #this means we don't even have the meta table in there... no problem,
                        log.debug('Creating DB for the first time')
                    else:
                        #something went wrong
                        log.error("Can't update DB: %s", e)
                if db_perform_update_step: 
                    #we need to perform this update step
                    log.debug('Updating %s to version %s', table_name, version)
                    for sql_item in self.__tables[table_name][version]:
                        log.debug('Updating Schema: %s', sql_item)
                        self._getConnection().execute(sql_item)
    
    def isInitialized(self):
        """If this DB is initialized and its Schema up to date."""
        try:
            rows = self._getConnection().execute("SELECT table_name, max(version) FROM meta GROUP BY table_name;").fetchall()
            if not rows or rows[0] is None or rows[0][0] is None: return False
            tables = set([item[0] for item in rows])    #store the table names found
            for row in rows:
                table_name, max_version = row
                if table_name in self.__tables and max(self.__tables[table_name]) > max_version:
                    return False 
            return not bool(tables.difference([table for table in self.__tables if not table.startswith('__')]))
        except:
            return False
        
    def storeHistory(self, tool, config_dict, result = None):
        """Store an analysis run
        Parameters:
        tool: pluginAbstract implementation
            the tool for which we are storing the information
        config_dict: dict
            dictionary with the run configuration
        result: dict
            dictionary with the results (created files)"""
        if result is None: result = {}
        row = (datetime.now(), 
                tool.__class__.__name__.lower(),    #for case insensitive search 
                repr(tool.__version__), 
                json.dumps(config_dict),
                json.dumps(result),)
        log.debug('Row: %s', row)
        self._getConnection().execute("INSERT INTO history(timestamp,tool,version,configuration,result) VALUES(?, ?, ?, ?,?);", row)
        
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
    
        