"""
Created on 23.05.2016

@author: Sebastian Illing
"""

from datetime import datetime, timedelta
import unittest
import os
import tempfile
import shutil
import logging
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG)

from evaluation_system.model.db import timestamp_to_string, timestamp_from_string
from evaluation_system.model.history.models import History, HistoryTag, ResultTag
from evaluation_system.model.plugins.models import Version
from evaluation_system.tests.mocks.dummy import DummyUser, DummyPlugin
from django.contrib.auth.models import User
from evaluation_system.model.solr_models.models import UserCrawl


class Test(unittest.TestCase):
    """Test the User construct used for managing the configuration of a user"""
    DUMMY_USER = {'pw_name':'someone'}

    def setUp(self):
        os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = os.path.dirname(__file__) + '/test.conf'
        User.objects.filter(username='dummy_user').delete()
        self.user = DummyUser(random_home=True, **Test.DUMMY_USER)
        self.db_user = User.objects.create(username='dummy_user')
        self.tool = DummyPlugin()
        self.config_dict = {'the_number': 42, 'number': 12, 'something': 'else', 'other': 'value', 'input': '/folder'}
        self.row_id = self.user.getUserDB().storeHistory(
            self.tool, self.config_dict, 'user', History.processStatus.not_scheduled, caption='My caption'
        )

    def tearDown(self):
        # remove the test entries from the database
        #User.objects.all().delete()
        History.objects.all().delete()
        User.objects.filter(username='dummy_user').delete()
        home = self.user.getUserHome()
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            # make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)


    def test_store_history(self):
        row_id = self.user.getUserDB().storeHistory(
            self.tool, self.config_dict, 'user', 1, caption='My caption'
        )
        h = History.objects.get(id=row_id)
        self.assertTrue(h)
        self.assertEqual(h.status_name(), 'finished_no_output')
        self.assertEqual(h.caption, 'My caption')
        self.assertEqual(h.config_dict(), self.config_dict)

    def test_schedule_entry(self):
        self.user.getUserDB().scheduleEntry(self.row_id, 'user', '/slurm/output/file.txt')
        h = History.objects.get(id=self.row_id)
        self.assertEqual(h.status, History.processStatus.scheduled)
        self.assertEqual(h.slurm_output, '/slurm/output/file.txt')

    def test_upgrade_status(self):

        self.assertRaises(self.user.getUserDB().ExceptionStatusUpgrade,
                          self.user.getUserDB().upgradeStatus, self.row_id, 'user', 6)

        self.user.getUserDB().upgradeStatus(self.row_id, 'user', History.processStatus.finished)
        h = History.objects.get(id=self.row_id)
        self.assertEqual(h.status, History.processStatus.finished)

    def test_change_flag(self):
        self.user.getUserDB().changeFlag(self.row_id, 'user', History.Flag.deleted)
        h = History.objects.get(id=self.row_id)
        self.assertEqual(h.flag, History.Flag.deleted)

    def test_get_history(self):
        # create some values
        users = ['user', 'other', 'user', 'test']
        for u in users:
            self.user.getUserDB().storeHistory(self.tool, self.config_dict, u, 1, caption='My %s' % u)

        history = self.user.getUserDB().getHistory()
        self.assertEqual(history.count(), 5)
        history = self.user.getUserDB().getHistory(uid='user')
        self.assertEqual(history.count(), 3)
        history = self.user.getUserDB().getHistory(uid='user', tool_name='dummyplugin', limit=2)
        self.assertEqual(history.count(), 2)
        history = self.user.getUserDB().getHistory(uid='user', entry_ids=self.row_id)
        self.assertEqual(history.count(), 1)

    def test_add_history_tag(self):
        self.user.getUserDB().addHistoryTag(self.row_id, HistoryTag.tagType.note_public, 'Some note')

        h = History.objects.get(id=self.row_id)
        tags = h.historytag_set.all()
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].type, HistoryTag.tagType.note_public)

    def test_update_history_tag(self):
        self.user.getUserDB().addHistoryTag(self.row_id, HistoryTag.tagType.note_public, 'Some note', uid='user')

        h_tag = History.objects.get(id=self.row_id).historytag_set.first()
        self.user.getUserDB().updateHistoryTag(h_tag.id, HistoryTag.tagType.note_deleted, 'New text', uid='user')

        h_tag = History.objects.get(id=self.row_id).historytag_set.first()
        self.assertEqual(h_tag.type, HistoryTag.tagType.note_deleted)
        self.assertEqual(h_tag.text, 'New text')

    def test_store_results(self):

        results = {'/some/result.png': {'type': 'plot', 'caption': 'super plot'},
                   '/some/other.eps': {'type': 'data'}}
        self.user.getUserDB().storeResults(self.row_id, results)

        h = History.objects.get(id=self.row_id)

        self.assertEqual(h.result_set.count(), 2)
        for key, val in results.iteritems():
            self.assertTrue(h.result_set.filter(history_id_id=self.row_id,
                                                output_file=key).exists())
            if val.get('caption', None):
                res_tag = h.result_set.get(output_file=key).resulttag_set.first()
                self.assertEqual(res_tag.type, ResultTag.flagType.caption)
                self.assertEqual(res_tag.text, val['caption'])

    def test_version(self):
        Version.objects.all().delete()
        # create version entry
        version_id = self.user.getUserDB().newVersion('dummyplugin', '1.0', 'git', 'git_number',
                                                      'tool_git', 'tool_git_number')
        self.assertTrue(Version.objects.filter(id=version_id).exists())

        # get version entry
        get_version_id = self.user.getUserDB().getVersionId('dummyplugin', '1.0', 'git', 'git_number',
                                                            'tool_git', 'tool_git_number')

        self.assertEqual(version_id, get_version_id)
        Version.objects.all().delete()

    def test_create_user(self):
        User.objects.filter(username='new_user').delete()
        self.user.getUserDB().createUser('new_user', 'test@test.de', 'Test', 'User')
        self.assertTrue(User.objects.filter(username='new_user').exists())
        User.objects.filter(username='new_user').delete()

    def test_create_user_crawl(self):
        self.user.getUserDB().create_user_crawl('/some/test/folder', 'user')
        self.assertTrue(UserCrawl.objects.filter(status='waiting', path_to_crawl='/some/test/folder').exists())
        UserCrawl.objects.all().delete()

    def test_timestamp_to_string(self):
        time = datetime.now()
        self.assertEqual(timestamp_to_string(time), time.strftime('%Y-%m-%d %H:%M:%S.%f'))

    def test_timestamp_from_string(self):
        time = datetime.now()
        time_str = timestamp_to_string(time)
        self.assertEqual(time, timestamp_from_string(time_str))