'''
Created on 12.12.2012

@author: estani
'''
from datetime import datetime, timedelta
import unittest
import os
import tempfile
import shutil
import logging
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG)

from evaluation_system.model.db import HistoryEntry, _status_running
from evaluation_system.tests.mocks import DummyUser, DummyPlugin

class Test(unittest.TestCase):
    """Test the User construct used for managing the configuration of a user"""
    DUMMY_USER = {'pw_name':'someone'}

    def setUp(self):
        self.user = DummyUser(random_home=True, **Test.DUMMY_USER)
        

    def tearDown(self):
        # remove the test entries from the database
        db = self.user.getUserDB()
        db._getConnection().execute("DELETE from history_history where uid='Test';")
        
        home = self.user.getUserHome()
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)

    def testCreation(self):
        user = DummyUser(random_home=True, pw_name='test1')
        home = user.getUserHome()
        
        db = user.getUserDB()
        # this assertion makes no sense for a global db
        # self.assertTrue(db._db_file.startswith(home))
        self.assertTrue(db.isInitialized())
        self.assertTrue(os.path.isfile(db._db_file))
        
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)
        
    def testInserts(self):
        db = self.user.getUserDB()
        entries = db._getConnection().execute("SELECT count(*) from history_history where uid='Test';").fetchone()[0]
        db.storeHistory(DummyPlugin(), dict(a=1), uid='Test', status=_status_running)
        self.assertEqual(db._getConnection().execute("SELECT count(*) from history_history where uid='Test';").fetchone()[0],
                         entries + 1)
        
        res = db._getConnection().execute("SELECT * from history_history where uid='Test';").fetchall()
        self.assertEqual(len(res), 1)
        res = res[0]
        self.assertEqual(res[2:5], ('dummyplugin', '(0, 0, 0)', '{"a": 1}'))
        
    def _timedeltaToDays(self, date_time):
        #=======================================================================
        # td = time_delta.microseconds / (24.0 * 60 * 60 * 1000000) + \
        #        time_delta.seconds / (24.0 * 60 * 60) + \
        #        time_delta.days
        #=======================================================================
        return HistoryEntry.timestampToString(date_time)
    
    def testGetHistory(self):
        db = self.user.getUserDB()
        self.assertEqual(db._getConnection().execute("SELECT count(*) from history_history where uid='Test';").fetchone()[0], 0)
        test_dicts = [dict(a=1), dict(a=1,b=2), dict(a=None,b=2)]
        for td in test_dicts:
            db.storeHistory(DummyPlugin(), td, uid='Test', status=_status_running)
        
        res = db._getConnection().execute("SELECT * from history_history where uid='Test';").fetchall()
        self.assertEqual(len(res), len(test_dicts))
        all_res = db.getHistory(uid='Test')
        self.assertEqual(len(all_res), len(test_dicts))
        
        #check the content and also the order. should be LIFO ordered
        test_dicts.reverse()
        count=0
        old_time=datetime(3000,1,1)
        version=(0,0,0)
        tool_name='DummyPlugin'.lower()
        for rd in all_res:
            tstamp = HistoryEntry.timestampFromString(rd.timestamp)
            self.assertTrue(tstamp < old_time)
            old_time = tstamp
            self.assertEqual(rd.tool_name, tool_name)
            self.assertEqual(rd.version, version)
            self.assertEqual(rd.configuration, test_dicts[count])
            count += 1
            
        self.assertEqual(len(db.getHistory(limit=1)), 1)
        self.assertEqual(db.getHistory(tool_name), all_res)
        #to assure some minimal time distance from last additions
        import time
        time.sleep(0.1)
        now1 = datetime.now()
        db.storeHistory(DummyPlugin(), dict(special='time1'), uid='Test', status=_status_running)
        time.sleep(0.1)
        now2 = datetime.now()
        db.storeHistory(DummyPlugin(), dict(special='time2'), uid='Test', status=_status_running)
        
        #check we get time1 and time2 when going 0.5 before now1
        res = db.getHistory(since=self._timedeltaToDays(now1-timedelta(seconds=0.05)))
        self.assertEqual(len(res), 2)
        self.assertEqual(set([r.configuration['special'] for r in res]), set(['time1','time2']))
        
        #check we get time2 when going 0.5 before now2
        res = db.getHistory(since=self._timedeltaToDays(now2-timedelta(seconds=0.05)))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].configuration['special'],'time2')
        
        #check we get time2 when going between 0.5 before now1 and 0.5 before now2
        res = db.getHistory(since=self._timedeltaToDays(now1-timedelta(seconds=0.05)),
                            until=self._timedeltaToDays(now2-timedelta(seconds=0.05)))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].configuration['special'],'time1')
        
    
    def testHistoryEntry(self):
        db = self.user.getUserDB()
        db.storeHistory(DummyPlugin(), dict(a=1), result={'/dummy/tmp/test/file1.png':{'timestamp':1,'type':'plot'},
                                                          '/dummy/tmp/test/file1.nc':{'timestamp':1,'type':'data'},},
                        uid='Test',
                        status=_status_running)
        all_entries = db.getHistory()
        print all_entries
        print all_entries[0].__str__()
        print all_entries[0].__str__(compact=False)
        
        #test date parsing
        values = [('2012-10-01 10:11:21', (2012, 10,1,10,11,21)),
                  ('2012-10-01 10:11', (2012, 10,1,10,11,0)),
                  ('2012-10-01 10', (2012, 10,1,10)),
                  ('2012-10-01', (2012, 10,1)),
                  ('2012-10', (2012, 10,1)),
                  ('2012', (2012, 1,1))]
        for date_str, date_tup in values:
            dt = HistoryEntry.timestampFromString(date_str)
            self.assertEquals(dt, datetime(*date_tup))
        
    def testSchemaUpgrade(self):
        pass
    
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()