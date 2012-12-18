'''
Created on 12.12.2012

@author: estani
'''
from evaluation_system.tests.mocks import DummyUser, DummyPlugin
from evaluation_system.api.plugin import metadict

from datetime import datetime, timedelta
import unittest
import os
import tempfile
import shutil
import logging
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG)

class Test(unittest.TestCase):
    """Test the User construct used for managing the configuratio of a user"""
    DUMMY_USER = {'pw_name':'someone'}

    def setUp(self):
        self.user = DummyUser(random_home=True, **Test.DUMMY_USER)
        

    def tearDown(self):
        home = self.user.getUserHome()
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)

    def testCreation(self):
        user = DummyUser(random_home=True, pw_name='test1')
        home = user.getUserHome()
        
        db = user.getUserDB()
        self.assertTrue(db._db_file.startswith(home))
        self.assertTrue(db.isInitialized())
        self.assertTrue(os.path.isfile(db._db_file))
        
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)
        
    def testInserts(self):
        db = self.user.getUserDB()
        self.assertEqual(db._getConnection().execute("SELECT count(*) from history;").fetchone()[0], 0)
        db.storeHistory(DummyPlugin(), dict(a=1))
        self.assertEqual(db._getConnection().execute("SELECT count(*) from history;").fetchone()[0], 1)
        
        res = db._getConnection().execute("SELECT * from history;").fetchall()
        self.assertEqual(len(res), 1)
        res = res[0]
        self.assertEqual(res[1:4], ('dummyplugin', '(0, 0, 0)', '{"a": 1}'))
        
    def _timedeltaToDays(self, time_delta):
        return time_delta.microseconds / (24.0 * 60 * 60 * 1000000) + \
                time_delta.seconds / (24.0 * 60 * 60) + \
                time_delta.days
                
    def testGetHistory(self):
        db = self.user.getUserDB()
        self.assertEqual(db._getConnection().execute("SELECT count(*) from history;").fetchone()[0], 0)
        test_dicts = [dict(a=1), dict(a=1,b=2), metadict(compact_creation=True,a=(None,dict(type=str)),b=2)]
        for td in test_dicts:
            db.storeHistory(DummyPlugin(), td)
        
        res = db._getConnection().execute("SELECT * from history;").fetchall()
        self.assertEqual(len(res), len(test_dicts))
        all_res = db.getHistory()
        self.assertEqual(len(all_res), len(test_dicts))
        
        #check the content and also the order. should be LIFO ordered
        test_dicts.reverse()
        count=0
        old_time=datetime(3000,1,1)
        version=(0,0,0)
        tool_name='DummyPlugin'.lower()
        for rd in all_res:
            self.assertTrue(rd.timestamp < old_time)
            old_time = rd.timestamp
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
        db.storeHistory(DummyPlugin(), dict(special='time1'))
        time.sleep(0.1)
        now2 = datetime.now()
        db.storeHistory(DummyPlugin(), dict(special='time2'))
        
        #check we get time1 and time2 when going 0.5 before now1
        from_days = self._timedeltaToDays(datetime.now()-now1+timedelta(seconds=0.05))
        res = db.getHistory(days_span=from_days)
        self.assertEqual(len(res), 2)
        self.assertEqual(set([r.configuration['special'] for r in res]), set(['time1','time2']))
        
        #check we get time2 when going 0.5 before now2
        from_days = self._timedeltaToDays(datetime.now()-now2+timedelta(seconds=0.05))
        res = db.getHistory(days_span=from_days)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].configuration['special'],'time2')
        
        #check we get time2 when going between 0.5 before now1 and 0.5 before now2
        from_days = (self._timedeltaToDays(datetime.now()-now1+timedelta(seconds=0.05)),
                     self._timedeltaToDays(datetime.now()-now2+timedelta(seconds=0.05)))
        res = db.getHistory(days_span=from_days)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].configuration['special'],'time1')
    
    def testHistoryEntry(self):
        db = self.user.getUserDB()
        db.storeHistory(DummyPlugin(), dict(a=1), result={'/dummy/tmp/test/file1.png':{'timestamp':1,'type':'plot'},
                                                          '/dummy/tmp/test/file1.nc':{'timestamp':1,'type':'data'},})
        all = db.getHistory()
        print all
        print all[0].__str__()
        print all[0].__str__(compact=False)
        
    def testSchemaUpgrade(self):
        pass
    
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()