from __future__ import annotations
import datetime
import os
import pytest
import mock


def test_broken_command(hist_obj, capsys, admin_env):
    from evaluation_system.tests import similar_string, run_cli
    from django.contrib.auth.models import User
    from evaluation_system.model.history.models import History

    History.objects.create(
        status=History.processStatus.finished,
        slurm_output="/some/out.txt",
        timestamp=datetime.datetime.now(),
        uid=User.objects.first(),
    )
    with mock.patch.dict(os.environ, admin_env, clear=True):
        run_cli(["check", "broken-runs"])
        cmd_out = capsys.readouterr().out
    assert f"Setting job {hist_obj.id} to broken\n" in cmd_out
    assert History.objects.get(id=hist_obj.id).status == History.processStatus.broken


def test_forbidden_usage(capsys, dummy_env):
    from evaluation_system.tests import run_cli
    from freva.cli.admin import check4broken_runs

    with pytest.raises(SystemExit):
        run_cli(["check", "--help"])
    assert "invalid choice" in capsys.readouterr().err
    with pytest.raises(RuntimeError):
        check4broken_runs()
