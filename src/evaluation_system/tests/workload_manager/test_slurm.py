from evaluation_system.api.workload_manager.slurm import SLURMJob


def test_header(tmpdir):
    log_directory = tmpdir.strpath
    with SLURMJob(walltime="00:02:00", processes=4, cores=8, memory="28GB") as cluster:
        assert "#SBATCH" in cluster.job_header
        assert "#SBATCH -J worker" in cluster.job_header
        assert "#SBATCH -n 1" in cluster.job_header
        assert "#SBATCH --cpus-per-task=8" in cluster.job_header
        assert "#SBATCH --mem=27G" in cluster.job_header
        assert "#SBATCH -t 00:02:00" in cluster.job_header
        assert "#SBATCH -p" not in cluster.job_header
        # assert "#SBATCH -A" not in cluster.job_header

    with SLURMJob(
        queue="regular",
        project="DaskOnSlurm",
        processes=4,
        cores=8,
        memory="28GB",
        job_cpu=16,
        job_mem="100G",
        log_directory=log_directory,
    ) as cluster:
        assert "#SBATCH --cpus-per-task=16" in cluster.job_header
        assert "#SBATCH --cpus-per-task=8" not in cluster.job_header
        assert "#SBATCH --mem=100G" in cluster.job_header
        assert "#SBATCH -t " in cluster.job_header
        assert "#SBATCH -A DaskOnSlurm" in cluster.job_header
        assert "#SBATCH -p regular" in cluster.job_header

    with SLURMJob(cores=4, memory="8GB") as cluster:
        assert "#SBATCH" in cluster.job_header
        assert "#SBATCH -J " in cluster.job_header
        assert "#SBATCH -n 1" in cluster.job_header
        assert "#SBATCH -t " in cluster.job_header
        assert "#SBATCH -p" not in cluster.job_header
        # assert "#SBATCH -A" not in cluster.job_header


def test_job_script():
    with SLURMJob(walltime="00:02:00", processes=4, cores=8, memory="28GB") as cluster:
        job_script = cluster.job_script()
        assert "#SBATCH" in job_script
        assert "#SBATCH -J worker" in job_script
        assert "#SBATCH -n 1" in job_script
        assert "#SBATCH --cpus-per-task=8" in job_script
        assert "#SBATCH --mem=27G" in job_script
        assert "#SBATCH -t 00:02:00" in job_script
        assert "#SBATCH -p" not in job_script
        # assert "#SBATCH -A" not in job_script

        assert "export " not in job_script

    with SLURMJob(
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
        assert "#SBATCH" in job_script
        assert "#SBATCH -J worker" in job_script
        assert "#SBATCH -n 1" in job_script
        assert "#SBATCH --cpus-per-task=8" in job_script
        assert "#SBATCH --mem=27G" in job_script
        assert "#SBATCH -t 00:02:00" in job_script
        assert "#SBATCH -p" not in job_script
        # assert "#SBATCH -A" not in job_script

        assert 'export LANG="en_US.utf8"' in job_script
        assert 'export LANGUAGE="en_US.utf8"' in job_script
        assert 'export LC_ALL="en_US.utf8"' in job_script


def test_slurm_format_bytes_ceil():
    from evaluation_system.api.workload_manager.slurm import slurm_format_bytes_ceil

    assert (
        slurm_format_bytes_ceil(1024**3 - 1) == "1024M"
    ), "Failed to round up just below 1G bytes"
    assert slurm_format_bytes_ceil(1024**2) == "1M", "Failed for exact 1M bytes"
    assert (
        slurm_format_bytes_ceil(1025) == "2K"
    ), "Failed to round up slightly over 1K bytes"
    assert (
        slurm_format_bytes_ceil(1022) == "1K"
    ), "Failed to round up slightly over 1K bytes"
