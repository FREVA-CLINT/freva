"""
Created on 23.05.2016

@author: Sebastian Illing
"""
import unittest
from datetime import datetime



def test_history_model(test_user):
    # test slurm id
    user, hist = test_user
    slurm_id = hist.slurmId()
    assert slurm_id == '44742'

    # test status_names
    status = hist.status_name()
    assert status == 'running'

    # test print history
    _str = hist.__str__(compact=True)

def test_result_model(test_user):
    from evaluation_system.model.history.models import Result
    user, hist = test_user
    r = Result.objects.create(
        history_id=hist,
        output_file='/some/paht/to_file.ext',
        preview_file='/path/to/preview.jpg',
        file_type=Result.Filetype.plot
    )

    assert Result.objects.filter(id=r.id).exists()

    # test get extension
    assert r.fileExtension() == '.ext'
