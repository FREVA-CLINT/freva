import pytest

from evaluation_system.api.workload_manager.moab import MoabJob
from evaluation_system.api.workload_manager.pbs import PBSJob


@pytest.mark.parametrize("Cluster", [PBSJob, MoabJob])
def test_header(Cluster):
    with Cluster(
        walltime="00:02:00", processes=4, cores=8, memory="28GB", name="worker"
    ) as cluster:

        assert "#PBS" in cluster.job_header
        assert "#PBS -N worker" in cluster.job_header
        assert "#PBS -l select=1:ncpus=8:mem=27GB" in cluster.job_header
        assert "#PBS -l walltime=00:02:00" in cluster.job_header
        assert "#PBS -q" not in cluster.job_header
        assert "#PBS -A" not in cluster.job_header

    with Cluster(
        queue="regular",
        project="DaskOnPBS",
        processes=4,
        cores=8,
        resource_spec="select=1:ncpus=24:mem=100GB",
        memory="28GB",
    ) as cluster:

        assert "#PBS -q regular" in cluster.job_header
        assert "#PBS -N worker" in cluster.job_header
        assert "#PBS -l select=1:ncpus=24:mem=100GB" in cluster.job_header
        assert "#PBS -l select=1:ncpus=8:mem=27GB" not in cluster.job_header
        assert "#PBS -l walltime=" in cluster.job_header
        assert "#PBS -A DaskOnPBS" in cluster.job_header

    with Cluster(cores=4, memory="8GB") as cluster:

        assert "#PBS -j oe" not in cluster.job_header
        assert "#PBS -N" in cluster.job_header
        assert "#PBS -l walltime=" in cluster.job_header
        assert "#PBS -A" not in cluster.job_header
        assert "#PBS -q" not in cluster.job_header

    with Cluster(cores=4, memory="8GB", job_extra=["-j oe"]) as cluster:

        assert "#PBS -j oe" in cluster.job_header
        assert "#PBS -N" in cluster.job_header
        assert "#PBS -l walltime=" in cluster.job_header
        assert "#PBS -A" not in cluster.job_header
        assert "#PBS -q" not in cluster.job_header


@pytest.mark.parametrize("Cluster", [PBSJob, MoabJob])
def test_job_script(Cluster):
    with Cluster(walltime="00:02:00", processes=4, cores=8, memory="28GB") as cluster:

        job_script = cluster.job_script()
        assert "#PBS" in job_script
        assert "#PBS -N worker" in job_script
        assert "#PBS -l select=1:ncpus=8:mem=27GB" in job_script
        assert "#PBS -l walltime=00:02:00" in job_script
        assert "#PBS -q" not in job_script
        assert "#PBS -A" not in job_script

    with Cluster(
        queue="regular",
        project="DaskOnPBS",
        processes=4,
        cores=8,
        resource_spec="select=1:ncpus=24:mem=100GB",
        memory="28GB",
    ) as cluster:

        job_script = cluster.job_script()
        assert "#PBS -q regular" in job_script
        assert "#PBS -N worker" in job_script
        assert "#PBS -l select=1:ncpus=24:mem=100GB" in job_script
        assert "#PBS -l select=1:ncpus=8:mem=27GB" not in job_script
        assert "#PBS -l walltime=" in job_script
        assert "#PBS -A DaskOnPBS" in job_script


def test_informative_errors():
    with pytest.raises(ValueError) as info:
        PBSJob(memory=None, cores=4)
    assert "memory" in str(info.value)
