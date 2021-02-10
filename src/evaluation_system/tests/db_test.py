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

import pytest


def test_store_history(dummy_history, dummy_user, dummy_plugin, config_dict):
    row_id = dummy_user.user.getUserDB().storeHistory(
        dummy_plugin, config_dict, 'user', 1, caption='My caption'
    )
    h = dummy_history.objects.get(id=row_id)
    assert h
    assert h.status_name() == 'finished_no_output'
    assert h.caption == 'My caption'
    assert h.config_dict() == config_dict

def test_schedule_entry(dummy_user, dummy_history):
    dummy_user.user.getUserDB().scheduleEntry(dummy_user.row_id,
                                              'user',
                                              '/slurm/output/file.txt')
    h = dummy_history.objects.get(id=dummy_user.row_id)
    assert h.status == dummy_history.processStatus.scheduled
    assert h.slurm_output == '/slurm/output/file.txt'

def test_upgrade_status(dummy_user, dummy_history):

    with pytest.raises(dummy_user.user.getUserDB().ExceptionStatusUpgrade):
        dummy_user.user.getUserDB().upgradeStatus(dummy_user.row_id, 'user', 6)

    dummy_user.user.getUserDB().upgradeStatus(dummy_user.row_id,
                                              'user',
                                              dummy_history.processStatus.finished)
    h = dummy_history.objects.get(id=dummy_user.row_id)
    assert h.status == dummy_history.processStatus.finished

def test_change_flag(dummy_user, dummy_history):
    dummy_user.user.getUserDB().changeFlag(dummy_user.row_id,
                                           'user', 
                                           dummy_history.Flag.deleted)
    h = dummy_history.objects.get(id=dummy_user.row_id)
    assert h.flag == dummy_history.Flag.deleted

def test_get_history(dummy_user, dummy_plugin, config_dict):
    # create some values
    users = ['user', 'other', 'user', 'test']
    for u in users:
        dummy_user.user.getUserDB().storeHistory(dummy_plugin,
                                                 config_dict,
                                                 u, 1, 
                                                 caption=f'My {u}')

    history = dummy_user.user.getUserDB().getHistory()
    assert history.count() == 6
    history = dummy_user.user.getUserDB().getHistory(uid='user')
    assert history.count() == 4
    history = dummy_user.user.getUserDB().getHistory(uid='user',
                                                     tool_name='dummyplugin',
                                                     limit=2)
    assert history.count() == 2
    history = dummy_user.user.getUserDB().getHistory(uid='user',
                                                    entry_ids=dummy_user.row_id)
    assert history.count() == 1

def test_add_history_tag(dummy_user, dummy_history):
    from evaluation_system.model.history.models import HistoryTag
    dummy_user.user.getUserDB().addHistoryTag(dummy_user.row_id,
                                              HistoryTag.tagType.note_public,
                                              'Some note')

    h = dummy_history.objects.get(id=dummy_user.row_id)
    tags = h.historytag_set.all()
    assert len(tags) == 1
    assert tags[0].type == HistoryTag.tagType.note_public

def test_store_results(dummy_user, dummy_history):

    results = {'/some/result.png': {'type': 'plot', 'caption': 'super plot'},
               '/some/other.eps': {'type': 'data'}}
    dummy_user.user.getUserDB().storeResults(dummy_user.row_id, results)

    h = dummy_history.objects.get(id=dummy_user.row_id)

    assert h.result_set.count() == 2
    for key, val in results.iteritems():
        assert h.result_set.filter(history_id_id=dummy_user.row_id,
                                            output_file=key).exists()
        if val.get('caption', None):
            res_tag = h.result_set.get(output_file=key).resulttag_set.first()
            assert res_tag.type == ResultTag.flagType.caption
            assert res_tag.text == val['caption']

def test_version(dummy_user):
    from evaluation_system.model.plugins.models import Version
    Version.objects.all().delete()
    # create version entry
    version_id = dummy_user.user.getUserDB().newVersion('dummyplugin',
                      '1.0', 'git', 'git_number',
                                                  'tool_git', 'tool_git_number')
    assert Version.objects.filter(id=version_id).exists()

    # get version entry
    get_version_id = dummy_user.user.getUserDB().getVersionId('dummyplugin',
                                                              '1.0',
                                                              'git',
                                                              'git_number',
                                                              'tool_git',
                                                              'tool_git_number')
    assert version_id == get_version_id
    Version.objects.all().delete()

def test_create_user(dummy_user):
    from django.contrib.auth.models import User
    User.objects.filter(username='new_user').delete()
    dummy_user.user.getUserDB().createUser('new_user',
                                           'test@test.de',
                                           'Test', 'User')
    assert User.objects.filter(username='new_user').exists()
    User.objects.filter(username='new_user').delete()

def test_create_user_crawl(dummy_user):
    from evaluation_system.model.solr_models.models import UserCrawl
    dummy_user.user.getUserDB().create_user_crawl('/some/test/folder', 'user')
    assert UserCrawl.objects.filter(status='waiting',
                                    path_to_crawl='/some/test/folder').exists()
    UserCrawl.objects.all().delete()

def test_timestamp_to_string():
    from evaluation_system.model.db import timestamp_to_string, timestamp_from_string
    time = datetime.now()
    assert timestamp_to_string(time) == time.strftime('%Y-%m-%d %H:%M:%S.%f')

def test_timestamp_from_string():
    from evaluation_system.model.db import timestamp_to_string, timestamp_from_string
    time = datetime.now()
    time_str = timestamp_to_string(time)
    assert time == timestamp_from_string(time_str)

