import os
from shutil import rmtree
import sys
from textwrap import dedent
import tempfile

import pytest

from evaluation_system.api.workload_manager.lsf import LSFJob, lsf_format_bytes_ceil
from evaluation_system.api.workload_manager.core import parse_bytes


def test_header():
    with LSFJob(walltime="00:02", processes=4, cores=8, memory="8GB") as cluster:

        assert "#BSUB" in cluster.job_header
        assert "#BSUB -J worker" in cluster.job_header
        assert "#BSUB -n 8" in cluster.job_header
        assert "#BSUB -M 8000" in cluster.job_header
        assert "#BSUB -W 00:02" in cluster.job_header
        assert "#BSUB -q" not in cluster.job_header
        assert "#BSUB -P" not in cluster.job_header

    with LSFJob(
        queue="general",
        project="DaskOnLSF",
        processes=4,
        cores=8,
        memory="28GB",
        ncpus=24,
        mem=100000000000,
    ) as cluster:

        assert "#BSUB -q general" in cluster.job_header
        assert "#BSUB -J worker" in cluster.job_header
        assert "#BSUB -n 24" in cluster.job_header
        assert "#BSUB -n 8" not in cluster.job_header
        assert "#BSUB -M 100000" in cluster.job_header
        assert "#BSUB -M 28000" not in cluster.job_header
        assert "#BSUB -W" in cluster.job_header
        assert '#BSUB -P "DaskOnLSF"' in cluster.job_header

    with LSFJob(
        queue="general",
        project="Dask On LSF",
        processes=4,
        cores=8,
        memory="28GB",
        ncpus=24,
        mem=100000000000,
    ) as cluster:

        assert "#BSUB -q general" in cluster.job_header
        assert "#BSUB -J worker" in cluster.job_header
        assert "#BSUB -n 24" in cluster.job_header
        assert "#BSUB -n 8" not in cluster.job_header
        assert "#BSUB -M 100000" in cluster.job_header
        assert "#BSUB -M 28000" not in cluster.job_header
        assert "#BSUB -W" in cluster.job_header
        assert '#BSUB -P "Dask On LSF"' in cluster.job_header

    with LSFJob(cores=4, memory="8GB") as cluster:

        assert "#BSUB -n" in cluster.job_header
        assert "#BSUB -W" in cluster.job_header
        assert "#BSUB -M" in cluster.job_header
        assert "#BSUB -q" not in cluster.job_header
        assert "#BSUB -P" not in cluster.job_header

    with LSFJob(cores=4, memory="8GB", job_extra=["-u email@domain.com"]) as cluster:

        assert "#BSUB -u email@domain.com" in cluster.job_header
        assert "#BSUB -n" in cluster.job_header
        assert "#BSUB -W" in cluster.job_header
        assert "#BSUB -M" in cluster.job_header
        assert "#BSUB -q" not in cluster.job_header
        assert "#BSUB -P" not in cluster.job_header


def test_job_script():
    with LSFJob(walltime="00:02", processes=4, cores=8, memory="28GB") as cluster:

        job_script = cluster.job_script()
        assert "#BSUB" in job_script
        assert "#BSUB -J worker" in job_script
        assert "#BSUB -n 8" in job_script
        assert "#BSUB -M 28000" in job_script
        assert "#BSUB -W 00:02" in job_script
        assert "#BSUB -q" not in cluster.job_header
        assert "#BSUB -P" not in cluster.job_header

    with LSFJob(
        queue="general",
        project="DaskOnLSF",
        processes=4,
        cores=8,
        memory="28GB",
        ncpus=24,
        mem=100000000000,
    ) as cluster:

        job_script = cluster.job_script()
        assert "#BSUB -q general" in cluster.job_header
        assert "#BSUB -J worker" in cluster.job_header
        assert "#BSUB -n 24" in cluster.job_header
        assert "#BSUB -n 8" not in cluster.job_header
        assert "#BSUB -M 100000" in cluster.job_header
        assert "#BSUB -M 28000" not in cluster.job_header
        assert "#BSUB -W" in cluster.job_header
        assert '#BSUB -P "DaskOnLSF"' in cluster.job_header

    with LSFJob(
        walltime="1:00",
        cores=1,
        memory="16GB",
        project="Dask On LSF",
        job_extra=["-R rusage[mem=16GB]"],
    ) as cluster:

        job_script = cluster.job_script()

        assert "#BSUB -J worker" in cluster.job_header
        assert "#BSUB -n 1" in cluster.job_header
        assert "#BSUB -R rusage[mem=16GB]" in cluster.job_header
        assert "#BSUB -M 16000000" in cluster.job_header
        assert "#BSUB -W 1:00" in cluster.job_header
        assert '#BSUB -P "Dask On LSF"' in cluster.job_header


def test_informative_errors():
    with pytest.raises(ValueError) as info:
        LSFJob(memory=None, cores=4)
    assert "memory" in str(info.value)


def lsf_unit_detection_helper(expected_unit, conf_text=None):
    temp_dir = tempfile.mkdtemp()
    current_lsf_envdir = os.environ.get("LSF_ENVDIR", None)
    os.environ["LSF_ENVDIR"] = temp_dir
    if conf_text is not None:
        with open(os.path.join(temp_dir, "lsf.conf"), "w") as conf_file:
            conf_file.write(conf_text)
    memory_string = "13GB"
    memory_base = parse_bytes(memory_string)
    correct_memory = lsf_format_bytes_ceil(memory_base, lsf_units=expected_unit)
    with LSFJob(memory=memory_string, cores=1) as cluster:
        assert "#BSUB -M %s" % correct_memory in cluster.job_header
    rmtree(temp_dir)
    if current_lsf_envdir is None:
        del os.environ["LSF_ENVDIR"]
    else:
        os.environ["LSF_ENVDIR"] = current_lsf_envdir


@pytest.mark.parametrize(
    "lsf_units_string,expected_unit",
    [
        ("LSF_UNIT_FOR_LIMITS=MB", "mb"),
        ("LSF_UNIT_FOR_LIMITS=G  # And a comment", "gb"),
        ("#LSF_UNIT_FOR_LIMITS=NotDetected", "kb"),
    ],
)
def test_lsf_unit_detection(lsf_units_string, expected_unit):
    conf_text = dedent(
        """
        LSB_JOB_MEMLIMIT=Y
        LSB_MOD_ALL_JOBS=N
        LSF_PIM_SLEEPTIME_UPDATE=Y
        LSF_PIM_LINUX_ENHANCE=Y
        %s
        LSB_DISABLE_LIMLOCK_EXCL=Y
        LSB_SUBK_SHOW_EXEC_HOST=Y
        """
        % lsf_units_string
    )
    lsf_unit_detection_helper(expected_unit, conf_text)


def test_lsf_unit_detection_without_file():
    lsf_unit_detection_helper("kb", conf_text=None)
