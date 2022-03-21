import sys

from evaluation_system.api.workload_manager.oar import OARJob


def test_header():
    with OARJob(walltime="00:02:00", processes=4, cores=8, memory="28GB") as cluster:
        assert "#OAR -n worker" in cluster.job_header
        assert "#OAR -l /nodes=1/core=8,walltime=00:02:00" in cluster.job_header
        assert "#OAR --project" not in cluster.job_header
        assert "#OAR -q" not in cluster.job_header

    with OARJob(
        queue="regular",
        project="DaskOnOar",
        processes=4,
        cores=8,
        memory="28GB",
        job_extra=["-t besteffort"],
    ) as cluster:
        assert "walltime=" in cluster.job_header
        assert "#OAR --project DaskOnOar" in cluster.job_header
        assert "#OAR -q regular" in cluster.job_header
        assert "#OAR -t besteffort" in cluster.job_header

    with OARJob(cores=4, memory="8GB") as cluster:
        assert "#OAR -n worker" in cluster.job_header
        assert "walltime=" in cluster.job_header
        assert "#OAR --project" not in cluster.job_header
        assert "#OAR -q" not in cluster.job_header


def test_job_script():
    with OARJob(walltime="00:02:00", processes=4, cores=8, memory="28GB") as cluster:
        job_script = cluster.job_script()
        assert "#OAR" in job_script
        assert "#OAR -n worker" in job_script
        assert "#OAR -l /nodes=1/core=8,walltime=00:02:00" in job_script
        assert "#OAR --project" not in job_script
        assert "#OAR -q" not in job_script

        assert "export " not in job_script

    with OARJob(
        walltime="00:02:00",
        processes=4,
        cores=8,
        memory="28GB",
        env_extra=[
            'export LANG="en_US.utf8"',
            'export LANGUAGE="en_US.utf8"',
            'export LC_ALL="en_US.utf8"',
        ],
    ) as cluster:
        job_script = cluster.job_script()
        assert "#OAR" in job_script
        assert "#OAR -n worker" in job_script
        assert "#OAR -l /nodes=1/core=8,walltime=00:02:00" in job_script
        assert "#OAR --project" not in job_script
        assert "#OAR -q" not in job_script

        assert 'export LANG="en_US.utf8"' in job_script
        assert 'export LANGUAGE="en_US.utf8"' in job_script
        assert 'export LC_ALL="en_US.utf8"' in job_script
