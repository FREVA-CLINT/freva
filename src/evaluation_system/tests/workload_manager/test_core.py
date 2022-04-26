import pytest


def test_get_cancel_command():
    from evaluation_system.api.workload_manager import cancel_command

    with pytest.raises(NotImplementedError):
        cancel_command("bla", 1000)
    assert "scancel" in cancel_command("slurm", 1000)
