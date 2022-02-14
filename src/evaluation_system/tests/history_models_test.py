"""
Created on 23.05.2016

@author: Sebastian Illing
"""
import unittest
from datetime import datetime
import pwd
import os


def test_history_model(test_user):
    # test slurm id
    user, hist = test_user
    slurm_id = hist.slurmId()
    assert slurm_id == "44742"

    # test status_names
    status = hist.status_name()
    assert status == "running"

    # test print history
    _str = hist.__str__(compact=True)


def test_result_model(test_user):
    from evaluation_system.model.history.models import Result

    user, hist = test_user
    r = Result.objects.create(
        history_id=hist,
        output_file="/some/paht/to_file.ext",
        preview_file="/path/to/preview.jpg",
        file_type=Result.Filetype.plot,
    )

    assert Result.objects.filter(id=r.id).exists()

    # test get extension
    assert r.fileExtension() == ".ext"


def test_similar_results(dummy_user, test_user):
    from evaluation_system.model.history.models import History, Configuration
    from evaluation_system.tests.mocks.dummy import DummyPlugin

    hists = []
    uid = os.getuid()
    udata = pwd.getpwuid(uid)
    for i in range(10):
        hists += [
            dummy_user.user.getUserDB().storeHistory(
                tool=DummyPlugin(),
                config_dict={
                    "the_number": 42,
                    "number": 12,
                    "something": "else",
                    "other": "value",
                    "input": "/folder",
                    "variable": "pr",
                },
                status=0,
                uid=udata.pw_name,
            )
        ]

    hist = History.objects.create(
        timestamp=datetime.now(),
        status=History.processStatus.running,
        uid=test_user[0],
        configuration="{'the_number': 42, 'number': 12, 'something': 'else', 'other': 'value', 'input': '/folder', 'variable': 'pr'}",
        tool="dummytool",
        slurm_output="/path/to/slurm-44742.out",
    )

    o = Configuration.objects.filter(history_id=hist)
    sim_res = History.find_similar_entries(o)
    assert len(sim_res) == 0
