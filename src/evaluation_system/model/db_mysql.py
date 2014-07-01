'''
.. moduleauthor:: estani <estanislao.gonzalez@met.fu-berlin.de>

This modules encapsulates all access to databases.
'''
import sqlite3
import MySQLdb
MySQLdb.paramstyle = 'qmark'
from datetime import datetime
import json
import ast
import os
import re
import logging
from evaluation_system.misc import py27, config
log = logging.getLogger(__name__)

#Store sqlite3 file and pool
_connection_pool = {}

# be aware this is a hard-coded version of history.models.History.processStatus
_status_finished = 0
_status_finished_no_output = 1
_status_broken = 2
_status_running = 3
_status_scheduled = 4
_status_not_scheduled = 5

_result_preview = 0
_result_plot = 1
_result_data = 2
_result_unknown = 9

_resulttag_caption = 0


class HistoryEntry(object):
    """This object encapsulates the access to an entry in the history DB representing an analysis
the user has done in the past."""
    TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S.%f'
    """This timestamp format is used for parsing times when referring to a history entry and displaying them.""" 
    
    @staticmethod
    def timestampToString(datetime_obj):
        """This is the inverse of :class:`HistoryEntry.timestampFromString`. The formatting is defined by
:class:`TIMESTAMP_FORMAT`.

:returns: a string as formated out of a (:py:class:`datetime.datetime`) object.""" 
        return datetime_obj.strftime(HistoryEntry.TIMESTAMP_FORMAT)
    
    @staticmethod
    def timestampFromString(date_string):
        """This is the inverse of :class:`HistoryEntry.timestampToString`. The parsing is defined by
:class:`TIMESTAMP_FORMAT` and every sub-set of it generated by dropping the lower resolution time
values, e.g. dropping everything with a higher resolution than minutes (i.e. dropping seconds and microseconds).

:returns: a (:py:class:`datetime.datetime`) object as parsed from the given string.""" 
        tmp_format = HistoryEntry.TIMESTAMP_FORMAT
        while tmp_format:
            try:
                return datetime.strptime(date_string, tmp_format)
            except:
                pass
            tmp_format = tmp_format[:-3]    #removing last entry and separator (one of ' :-')
        raise ValueError("Can't parse a date out of '%s'" % date_string)
    
    def __init__(self, row):
        """Creates an entry out of the row returned by a DB proxy.

:param row: the DB row for which this entry will be created.
"""
	#print len(row)
        self.rowid = row[0]
        self.timestamp = str(row[1]) #datetime object
        self.tool_name = row[2]
        self.version = ast.literal_eval(row[3]) if row[3] else (None,None,None)
        self.configuration = json.loads(row[4]) if row[4] else {}
        self.results = []#json.loads(row[5]) if row[5] else {}
        self.slurm_output = row[5]
        self.uid = row[6]
        self.status = row[7]
        self.flag = row[8]
        self.version_details_id = row[9]
        
    def toJson(self):
        return json.dumps(dict(rowid=self.rowid, timestamp=self.timestamp.isoformat(), tool_name=self.tool_name,
             version=self.version, configuration=self.configuration, results=self.results,status=self.status))
        
    def __eq__(self, hist_entry):
        if isinstance(hist_entry, HistoryEntry):
            return self.rowid == hist_entry.rowid and self.timestamp == hist_entry.timestamp and \
                    self.tool_name == hist_entry.tool_name and self.version == hist_entry.version and \
                    self.configuration == hist_entry.configuration
    def __str__(self, compact=True):
        if compact:
            out_files = []
            for f in self.results:
                out_files.append(os.path.basename(f))
            conf_str = ', '.join(out_files) + ' ' + str(self.configuration)
            if len(conf_str) > 70:
                conf_str = conf_str[:67] + '...'
            version = '' 
        else:
            items = ['%15s=%s' % (k,v) for k,v in sorted(self.configuration.items())]
            if items:
                #conf_str = '\n' + json.dumps(self.configuration, sort_keys=True, indent=2)
                conf_str = '\nConfiguration:\n%s' % '\n'.join(items)
            if self.results:
                out_files = []
                for out_file, metadata in self.results.items():
                    status = 'deleted'
                    if os.path.isfile(out_file):
                        if 'timestamp' in metadata and os.path.getctime(out_file) - metadata['timestamp'] <= 0.9:
                            status = 'available'
                        else:
                            status = 'modified' 
                    out_files.append('  %s (%s)' % (out_file, status))
                conf_str = '%s\nOutput:\n%s' % (conf_str, '\n'.join(out_files))
                    
                    

            version = ' v%s.%s.%s' % self.version
            
        
        return '%s) %s%s [%s] %s' % (self.rowid, self.tool_name, version, self.timestamp, conf_str)
        
class UserDB(object):
    '''Encapsulates access to the local DB of a single user.

The main idea is to have a DB for storing the analysis runs.
At the present time the DB stores who did what when and what resulted out of it.
This class will just provide the methods for retrieving and storing this information.
There will be no handling of configuration in here.

Furthermore this class has a schema migration functionality that simplifies modification
of the DB considerably without the risk of loosing information.'''
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
                                        
    def safeExecute(self, *args, **kwargs):
        '''
        This is a wrapper for the execute function.
        It reconnects to the database when needed.
        '''
        ret = None
        
        try:
            cur = self._getConnection()
            res = cur.execute(*args, **kwargs)
        except (AttributeError, MySQLdb.OperationalError):
            log.debug('Re-connect to database')
            _connection_pool.pop(self._db_file, None)
            cur = self._getConnection()
            res = cur.execute(*args, **kwargs)
            
        return (cur, res)

    def safeExecutemany(self, *args, **kwargs):
        '''
        This is a wrapper for the execute function.
        It reconnects to the database when needed.
        '''
        ret = None
        
        try:
            cur = self._getConnection()
            res = cur.executemany(*args, **kwargs)
        except (AttributeError, MySQLdb.OperationalError):
            log.debug('Re-connect to database')
            _connection_pool.pop(self._db_file, None)
            cur = self._getConnection()
            res = cur.executemany(*args, **kwargs)
            
        return (cur, res)


    def __init__(self, user):
        '''As it is related to a user the user should be known at construction time.
Right now we have a descentralized sqllite DB per user stored in their configuration directory.
This might (and will) change in the future when we move to a more centralized architecture,
but at the present time the system works as a toolbox that the users start from the console.

:param user: the user this DB access relates to.
:type user: :class:`evaluation_system.model.user.User`
'''
        self._user = user
        #self._db_file = user.getUserConfigDir(create=True) + '/history.sql3'
        self._db_file = config.get(config.DATABASE_FILE, "")
        #print self.db_file
        self.initialize()
    
    def _getConnection(self):
        #trying to avoid holding a lock to the DB for too long
        if self._db_file not in _connection_pool:
#            _connection_pool[self._db_file] = sqlite3.connect(self._db_file,
#                                                              timeout=config.DATABASE_TIMEOUT,
#                                                              isolation_level=None,
#                                                              detect_types=sqlite3.PARSE_DECLTYPES)
            #MySQLdb.paramstyle = 'qmark'
            _connection_pool[self._db_file] = MySQLdb.connect(host="136.172.30.208", # your host, usually localhost
                                                              user="evaluationsystem", # your username
                                                              passwd="miklip", # your password
                                                              db="evaluationsystemtest") # name of the data base
            
            
            #_connection_pool[self._db_file].execute('PRAGMA synchronous = OFF')
            _connection_pool[self._db_file].paramstyle = 'qmark'                                       
        else:
            #check if still connected
            if not _connection_pool[self._db_file].open:
                # remove db from dictionary and try again
                _connection_pool.pop(self._db_file, None)
                return self._getConnection()

        return _connection_pool[self._db_file].cursor()
    
    def initialize(self, tool_name=None):
        """If not already initialized it will performed the required actions.
There might be differences as how tools are initialized (maybe multiple DBs/tables),
so if given, the initialization from a specific tool will be handled.
While initializing the schemas will get upgraded if required.

:param tool_name: name of the tool whose DB/table will get initialized. We are not using
                  this at this time, but to keep the DB as flexible as possible please provide this
                  information if available."""
        if not self.isInitialized():
            #well we need to walk throw history and replay what's missing. We assume a monotone increasing timeline
            #so when the first missing step is found, it as well as all the remining ones need to be replayed.
            #in order to update this DB state to the latest known one.
            for table_name, version in self.__tables['__order']:
                db_perform_update_step = True
                try:
                    (res, tmp) = self.safeExecute('SELECT * FROM meta WHERE table_name = %s AND version = %s', (table_name, version))
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
                        self.safeExecute(sql_item)
    
    def isInitialized(self):
        """:returns: (bool) If this DB is initialized and its Schema up to date."""
#        try:
#            rows = self._getConnection().execute("SELECT table_name, max(version) FROM meta GROUP BY table_name;").fetchall()
#            if not rows or rows[0] is None or rows[0][0] is None: return False
#            tables = set([item[0] for item in rows])    #store the table names found
#            for row in rows:
#                table_name, max_version = row
#                if table_name in self.__tables and max(self.__tables[table_name]) > max_version:
#                    return False 
#            return not bool(tables.difference([table for table in self.__tables if not table.startswith('__')]))
#        except:
#            return False
        return True
        
    def storeHistory(self, tool, config_dict, uid, status,
                     slurm_output = None, result = None, flag = None, version_details = None):
        """Store a an analysis run into the DB.

:type tool: :class:`evaluation_system.api.plugin.pluginAbstract`
:param tool: the plugin for which we are storing the information.
:param config_dict: dictionary with the configuration used for this run,
:param uid: the user id (useful in a global database)
:param status: the process status
:param result: dictionary with the results (created files).
"""
        if result is None: result = {}
        if slurm_output is None: slurm_output = 0
        if flag is None: flag = 0
        if version_details is None: version_details = 1
        row = (datetime.now(), 
                tool.__class__.__name__.lower(),    #for case insensitive search 
                repr(tool.__version__), 
                json.dumps(config_dict),
#                json.dumps(result),
                slurm_output,
                uid,
                status,
                flag,
                version_details)
        log.debug('Row: %s', row)
        
        (cur, res) = self.safeExecute("""INSERT INTO history_history(timestamp,tool,version,configuration,slurm_output,uid,status,flag,version_details_id) VALUES(%s, %s, %s, %s, %s, %s, %s,%s,%s);""", row)
        
        return cur.lastrowid

    def scheduleEntry(self, row_id, uid, slurmFileName):
        """
        :param row_id: The index in the history table
        :param uid: the user id
        :param slurmFileName: The slurm file belonging to the history entry
        Sets the name of the slurm file 
        """
        
        update_str='UPDATE history_history SET slurm_output=%s, status=%s ' 
        update_str+='WHERE id=%s AND uid=%s AND status=%s'
        
        entries = (slurmFileName,
                   _status_scheduled,
                   row_id,
                   uid,
                   _status_not_scheduled)
        self.safeExecute(update_str, entries)
        
        
    class ExceptionStatusUpgrade(Exception):
        """
        Exception class for failing status upgrades
        """
        def __init__(self, msg="Status could not be upgraded"):
            super(UserDB.ExceptionStatusUpgrade, self).__init__(msg)
        
        
    def upgradeStatus(self, row_id, uid, status):
        """
        :param row_id: The index in the history table
        :param uid: the user id
        :param status: the new status 
        After validation the status will be upgraded. 
        """
        
        select_str='SELECT status FROM history_history WHERE id=%s AND uid=%s'
        
        (cur, res) = self.safeExecute(select_str, (row_id,uid))

        rows = cur.fetchall()
        
        # check if only one entry is in the database
        if len(rows) != 1:
            raise self.ExceptionStatusUpgrade("No unique database entry found!")
        
        # only a status with a smaller number can be set
        st = int(rows[0][0])
        
        if(st < status):
            raise self.ExceptionStatusUpgrade('Tried to downgrade a status')
        
        # finally, do the SQL update
        update_str='UPDATE history_history SET status=%s WHERE id=%s AND uid=%s'                  
        self.safeExecute(update_str, (status, row_id, uid))
        
    def changeFlag(self, row_id, uid, flag):
        """
        :param row_id: The index in the history table
        :param uid: the user id
        :param flag: the new flag 
        After validation the status will be upgraded. 
        """
        
        select_str="SELECT flag FROM history_history WHERE id=%s AND uid=%s"

        
        (cur, res) = self.safeExecute(select_str, (row_id,uid))

        rows = cur.fetchall()
        
        # check if only one entry is in the database
        if len(rows) != 1:
            #print "SQL: ", select_str, row_id, uid, rows, len(rows), res, rows[0]
            raise self.ExceptionStatusUpgrade("No unique database entry found!")
                
        # finally, do the SQL update
        update_str='UPDATE history_history SET flag=%s WHERE id=%s AND uid=%s'                  
        self.safeExecute(update_str, (flag, row_id, uid))
        
    def getHistory(self, tool_name=None, limit=-1, since=None, until=None, entry_ids=None, uid=None):
        """Returns the stored history (run analysis) for the given tool.

:type tool_name: str
:param tool_name: name of the tool for which the information will be gathered (if None, then everything is returned).
:type limit: int
:param limit: Amount of rows to be returned (if < 0, return all).
:type since: datetime.datetime
:param since: Return only items stored after this date
:type until: datetime.datetime
:param until: Return only  items stored before this date
:param entry_ids: ([int] or int) id or list thereof to be selected
:returns: ([:class:`HistoryEntry`]) list of entries that match the query.
"""
        #print uid
        #ast.literal_eval(node_or_string)
        sql_params = []
        sql_str = "SELECT * FROM history_history"
        if tool_name or since or until or entry_ids or uid:
            sql_str = '%s WHERE "1"="1"' % sql_str
            if entry_ids is not None:
                if isinstance(entry_ids, int): entry_ids=[entry_ids]
                sql_str = '%s AND id in (%s)' % (sql_str, ','.join(map(str,entry_ids)))
                sql_params.extend(entry_ids)
            if tool_name is not None:
                sql_str = "%s AND tool='%s'" % (sql_str, tool_name.lower())
                sql_params.append(tool_name.lower())    #make search case insensitive
            if since is not None:
                sql_str = '%s AND timestamp > %s' % (sql_str, since)
                sql_params.append(since)
            if until is not None:
                sql_str = '%s AND timestamp < %s' % (sql_str, until)
                sql_params.append(until)
            if uid is not None:
                sql_str = "%s AND uid='%s'" % (sql_str, uid)
                sql_params.append(uid)
                    
        sql_str = sql_str + ' ORDER BY id DESC'
        if limit > 0:
            sql_str = '%s LIMIT %s' % (sql_str, limit)
            sql_params.append(limit)
        #print sql_str     
        #log.debug('sql: %s - (%s)', sql_str, tuple(sql_params))
        log.debug('Execute: %s' % sql_str)
        (cur, ret) = self.safeExecute(sql_str)
        res = cur.fetchall()
        return [HistoryEntry(row) for row in res]
    
    def storeResults(self, rowid, results):
        """
        :type rowid: integer
        :param rowid: the row id of the history entry where the results belong to
        :type results: dict with entries {str : dict} 
        :param results: meta-dictionary with meta-data dictionaries assigned to the file names.
        """
        
        data_to_store = []

        # regex to get the relative path
        expression = '(%s\\/*){1}(.*)' % re.escape(config.PREVIEW_PATH)
        reg_ex = re.compile(expression)

        for file_name in results:
            metadata = results[file_name]
            
            type_name = metadata.get('type','')
            type_number = _result_unknown
            
            preview_path = metadata.get('preview_path', '')
            preview_file = ''

            if preview_path:
                # We store the relative path for previews only.
                # Which allows us to move the preview files to a different folder.
                preview_file = reg_ex.match(preview_path).group(2)
                        
            if type_name == 'plot':
                type_number = _result_plot
            elif type_name == 'data':
                type_number = _result_data
                
            data_to_store = (rowid, file_name, preview_file, type_number)
            
            
            insert_string = 'INSERT INTO history_result(history_id_id, output_file, preview_file, file_type) VALUES (%s, %s, %s, %s)'
        
            (cur, res) =  self.safeExecute(insert_string, data_to_store)
            result_id = cur.lastrowid
            self._storeResultTags(result_id, metadata)
            


    def _storeResultTags(self, result_id, metadata):
        """
        :type result_id: integer
        :param result_id: the id of the result entry where the tag belongs to
        :type metadata: dict with entries {str : dict} 
        :param metadata: meta-dictionary with meta-data dictionaries assigned to the file names.
        """
        
        data_to_store = []


        # append new tags here        
        caption = metadata.get('caption', None)

        if caption:
            data_to_store.append((result_id, _resulttag_caption, caption))
                        
        insert_string = 'INSERT INTO history_resulttag(result_id_id, type, text) VALUES (%s, %s, %s)'
        
        self.safeExecutemany(insert_string, data_to_store)
        
    
        
    def getVersionId(self, toolname, version, repos_api, internal_version_api, repos_tool, internal_version_tool):
        repository = '%s;%s' % (repos_tool, repos_api)
        
        sqlstr = 'SELECT id FROM plugins_version WHERE'
        sqlstr += ' TOOL="%s"' % toolname
        sqlstr += ' AND VERSION="%s"' % version
        sqlstr += ' AND INTERNAL_VERSION_TOOL="%s"' % internal_version_tool
        sqlstr += ' AND INTERNAL_VERSION_API="%s"' % internal_version_api
        sqlstr += ' AND REPOSITORY="%s"' % repository

        (cur, res) = self.safeExecute(sqlstr)

        rows = cur.fetchall()
        
        # check if only one entry is in the database
        if len(rows) < 1:
            return None
        
        else:
            return rows[0][0]

    def newVersion(self, toolname, version, repos_api, internal_version_api, repos_tool, internal_version_tool):
        repository = '%s;%s' % (repos_tool, repos_api)
        
        sqlstr = 'INSERT INTO plugins_version '
        sqlstr += '(TIMESTAMP, TOOL, VERSION, INTERNAL_VERSION_TOOL, INTERNAL_VERSION_API, REPOSITORY)'
        sqlstr += 'VALUES (%s, %s, %s, %s, %s, %s)'
        
        timestamp = HistoryEntry.timestampToString(datetime.now())
        
        values = (timestamp, toolname, version, internal_version_tool, internal_version_api, repository)

        
        (cur, res) = self.safeExecute(sqlstr, values)

        result_id = cur.lastrowid
        
        return result_id

   
