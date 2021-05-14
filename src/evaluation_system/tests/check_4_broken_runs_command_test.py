import datetime
import pytest
import sys

from evaluation_system.tests import similar_string

def test_broken_command(broken_run, hist_obj, stdout):


    from django.contrib.auth.models import User
    from evaluation_system.model.history.models import History

    History.objects.create(
            status=History.processStatus.finished,
            slurm_output='/some/out.txt',
            timestamp=datetime.datetime.now(),
            uid=User.objects.first()
    )
    sys.stdout = stdout
    stdout.startCapturing()
    stdout.reset()
    broken_run.run([])
    stdout.stopCapturing()
    cmd_out = stdout.getvalue()
    assert f'Setting job {hist_obj.id} to broken\n' in cmd_out
    assert History.objects.get(id=hist_obj.id).status == History.processStatus.broken


