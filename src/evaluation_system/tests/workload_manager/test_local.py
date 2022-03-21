from evaluation_system.api.workload_manager.local import LocalJob
import pytest


def test_header():
    with LocalJob(walltime="00:02:00", processes=4, cores=8) as cluster:
        cluster.start()
        assert cluster.job_header == ""


def test_job_script():
    with LocalJob("test", env_extra=["source test"], log_directory="/tmp") as cluster:
        cluster.start()
        job_script = cluster.job_script()

        assert "source test" in job_script
        assert "/tmp/test" in job_script

    with LocalJob(
        env_extra=[
            'export LANG="en_US.utf8"',
            'export LANGUAGE="en_US.utf8"',
            'export LC_ALL="en_US.utf8"',
        ],
        log_directory="/tmp",
    ) as cluster:
        cluster.start()
        job_script = cluster.job_script()
        assert 'export LANG="en_US.utf8"' in job_script
        assert 'export LANGUAGE="en_US.utf8"' in job_script
        assert 'export LC_ALL="en_US.utf8"' in job_script
        assert "/tmp/worker" in job_script
