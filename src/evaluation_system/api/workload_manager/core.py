from __future__ import annotations
from contextlib import contextmanager, suppress
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import string
import tempfile
import abc
from typing import Any, Iterator, ClassVar, Optional, Union
from evaluation_system.misc import logger


def parse_bytes(s: Union[str, float, int]) -> int:
    """Parse byte string to numbers

    >>> from dask.utils import parse_bytes
    >>> parse_bytes('100')
    100
    >>> parse_bytes('100 MB')
    100000000
    >>> parse_bytes('100M')
    100000000
    >>> parse_bytes('5kB')
    5000
    >>> parse_bytes('5.4 kB')
    5400
    >>> parse_bytes('1kiB')
    1024
    >>> parse_bytes('1e6')
    1000000
    >>> parse_bytes('1e6 kB')
    1000000000
    >>> parse_bytes('MB')
    1000000
    >>> parse_bytes(123)
    123
    >>> parse_bytes('5 foos')
    Traceback (most recent call last):
        ...
    ValueError: Could not interpret 'foos' as a byte unit
    """
    if isinstance(s, (int, float)):
        return int(s)
    s = s.replace(" ", "")
    if not any(char.isdigit() for char in s):
        s = "1" + s

    for i in range(len(s) - 1, -1, -1):
        if not s[i].isalpha():
            break
    index = i + 1

    prefix = s[:index]
    suffix = s[index:]

    try:
        n = float(prefix)
    except ValueError as e:
        raise ValueError("Could not interpret '%s' as a number" % prefix) from e
    byte_sizes = {
        "kB": 10**3,
        "MB": 10**6,
        "GB": 10**9,
        "TB": 10**12,
        "PB": 10**15,
        "KiB": 2**10,
        "MiB": 2**20,
        "GiB": 2**30,
        "TiB": 2**40,
        "PiB": 2**50,
        "B": 1,
        "": 1,
    }
    byte_sizes = {k.lower(): v for k, v in byte_sizes.items()}
    byte_sizes.update({k[0]: v for k, v in byte_sizes.items() if k and "i" not in k})
    byte_sizes.update({k[:-1]: v for k, v in byte_sizes.items() if k and "i" in k})

    try:
        multiplier = byte_sizes[suffix.lower()]
    except KeyError as e:
        raise ValueError("Could not interpret '%s' as a byte unit" % suffix) from e

    result = n * multiplier
    return int(result)


@contextmanager
def tmpfile(**kwargs) -> Iterator[Path]:
    """
    Function to create and return a unique temporary file with the given
    extension, if provided.

    Parameters
    ----------
    kwargs :
        Keyword arguments to be passed to tempfile.NamedTemporaryFile

    Returns
    -------
    out : Path
        Path to the temporary file

    See Also
    --------
    NamedTemporaryFile : Built-in alternative for creating temporary files
    tmp_path : pytest fixture for creating a temporary directory unique to
               the test invocation
    """
    with tempfile.NamedTemporaryFile(**kwargs) as tf:
        yield Path(tf.name)


def string_to_bytes(size: str) -> float:
    """Convert a size string to int."""

    mul_dec = dict(pb=1000**5, tb=1000**4, gb=1000**3, mb=1000**2, kb=1000, b=1)
    mul_bi = dict(
        pib=1024**5,
        tib=1024**4,
        gib=1024**3,
        mib=1024**2,
        kib=1024,
    )
    num = ""
    byte_form = ""
    for s in str(size).lower().strip():
        if s:
            if s not in string.ascii_lowercase:
                num += s
            else:
                byte_form += s
    if len(byte_form) == 1:
        byte_form += "b"
    try:
        return float(num) * mul_dec[byte_form]
    except KeyError:
        try:
            return float(num) * mul_bi[byte_form]
        except KeyError:
            return float(num)


def format_bytes(n: int) -> str:
    """Format bytes as text

    >>> from dask.utils import format_bytes
    >>> format_bytes(1)
    '1 B'
    >>> format_bytes(1234)
    '1.21 kiB'
    >>> format_bytes(12345678)
    '11.77 MiB'
    >>> format_bytes(1234567890)
    '1.15 GiB'
    >>> format_bytes(1234567890000)
    '1.12 TiB'
    >>> format_bytes(1234567890000000)
    '1.10 PiB'

    For all values < 2**60, the output is always <= 10 characters.
    """
    for prefix, k in (
        ("Pi", 2**50),
        ("Ti", 2**40),
        ("Gi", 2**30),
        ("Mi", 2**20),
        ("ki", 2**10),
    ):
        if n >= k * 0.9:
            return f"{n / k:.2f} {prefix}B"
    return f"{n} B"


class Job(abc.ABC):
    """Base class to launch workers on Job queues

    This class should not be used directly, use a class appropriate for
    your queueing system (e.g. PBScluster or SLURMCluster) instead.

    Parameters
    ----------

    Attributes
    ----------
    submit_command: str
        Abstract attribute for job scheduler submit command,
        should be overridden
    cancel_command: str
        Abstract attribute for job scheduler cancel command,
        should be overridden

    See Also
    --------
    PBSCluster
    SLURMCluster
    SGECluster
    OARCluster
    LSFCluster
    MoabCluster
    """

    _script_template = (
        "%(shebang)s\n\n%(job_header)s\n%(env_header)s\n\n%(worker_command)s"
    )

    # Following class attributes should be overridden by extending classes.
    submit_command: ClassVar[str] = ""
    cancel_command: ClassVar[str] = ""
    config_name: ClassVar[Optional[str]] = None
    job_id_regexp: ClassVar[str] = r"(?P<job_id>\d+)"

    @abc.abstractmethod
    def __init__(
        self,
        name: Optional[str] = None,
        processes: Optional[int] = None,
        local_directory: Optional[Union[str, Path]] = None,
        env_extra: Optional[list[str]] = None,
        header_skip: Optional[list[str]] = None,
        log_directory: Optional[Union[str, Path]] = None,
        memory: Optional[Union[int, str]] = None,
        job_cpu: int = 1,
        cores: int = 2,
        shebang: str = "#!/usr/bin/env bash",
        python: str = sys.executable,
        scheduler: Optional[str] = "freva-plugin",
        freva_args: Optional[list[str]] = None,
        delete_job_script: bool = True,
        **kwargs,
    ):
        self.job_id = ""
        self.memory: int = 0
        env_extra = env_extra or []
        freva_args = freva_args or []
        super().__init__()
        self.job_header = ""
        # Keep information on process, cores, and memory, for use in subclasses
        try:
            self.worker_memory = string_to_bytes(str(memory))
        except ValueError:
            raise ValueError(f"Could not set scheduler memory {str(memory)}")
        self.delete_job_script = delete_job_script
        self.scheduler = scheduler or "freva-plugin"
        self.scheduler += " "
        self.worker_processes = processes
        self.worker_cores = cores or 2
        self.name = self.job_name = name or "worker"
        self.shebang = shebang
        self._env_header = "\n".join(filter(None, env_extra))
        self.header_skip = set(header_skip or [])
        self.log_directory = log_directory
        if self.log_directory is not None:
            if not os.path.exists(self.log_directory):
                os.makedirs(self.log_directory)
        self._command_template = self.scheduler + " ".join(map(str, freva_args))

    def job_script(self) -> str:
        """Construct a job submission script"""
        header = "\n".join(
            [
                line
                for line in self.job_header.split("\n")
                if not any(skip in line for skip in self.header_skip)
            ]
        )
        pieces = {
            "shebang": self.shebang,
            "job_header": header,
            "env_header": self._env_header,
            "worker_command": self._command_template,
        }
        return self._script_template % pieces

    @contextmanager
    def job_file(self) -> Iterator[Path]:
        """Write job submission script to temporary file"""
        with tmpfile(suffix=".sh", delete=self.delete_job_script) as fn:
            with open(fn, "w") as f:
                logger.debug("writing job script: \n%s", self.job_script())
                f.write(self.job_script())
            yield Path(fn)

    def _submit_job(self, script_filename: Union[str, Path]) -> Any:
        # Should we make this async friendly?
        return self._call(shlex.split(self.submit_command) + [str(script_filename)])

    def start(self) -> None:
        """Start workers and point them to our local scheduler"""
        logger.debug("Starting worker: %s", self.name)

        with self.job_file() as fn:
            out = self._submit_job(fn)
            job_id = self._job_id_from_submit_output(out)
            try:
                self.job_id = job_id
            except ValueError:
                self.job_id = "0"
        logger.debug("Starting job: %s", self.job_id)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def _job_id_from_submit_output(self, out: str) -> str:
        match = re.search(self.job_id_regexp, out)
        if match is None:
            msg = (
                "Could not parse job id from submission command "
                "output.\nJob id regexp is {!r}\nSubmission command "
                "output is:\n{}".format(self.job_id_regexp, out)
            )
            raise ValueError(msg)

        job_id = match.groupdict().get("job_id")
        if job_id is None:
            msg = (
                "You need to use a 'job_id' named group in your regexp, e.g. "
                "r'(?P<job_id>\\d+)'. Your regexp was: "
                "{!r}".format(self.job_id_regexp)
            )
            raise ValueError(msg)

        return job_id

    def close(self) -> None:
        logger.debug("Stopping worker: %s job: %s", self.name, self.job_id)
        self._close_job(self.job_id, self.cancel_command)

    @classmethod
    def _close_job(cls, job_id: str, cancel_command: str) -> None:
        if job_id:
            with suppress(RuntimeError):  # deleting job when job already gone
                cls._call(shlex.split(cancel_command) + [job_id])
            logger.debug("Closed job %s", job_id)

    @staticmethod
    def _call(command: list[str], **kwargs) -> str:
        """Call a command using subprocess.Popen.

        This centralizes calls out to the command line, providing consistent
        outputs, logging, and an opportunity to go asynchronous in the future.

        Parameters
        ----------
        command: List[str]
            A command, each of which is a list of strings to hand to
            subprocess.Popen

        Returns
        -------
        The stdout produced by the command, as string.

        Raises
        ------
        RuntimeError if the command exits with a non-zero exit code
        """
        cmd_str = " ".join(command)
        logger.debug(
            "Executing the following command to command line\n{}".format(cmd_str)
        )
        proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs
        )

        out, err = proc.communicate()
        out, err = out.decode(), err.decode()

        if proc.returncode != 0:
            raise RuntimeError(
                "Command exited with non-zero exit code.\n"
                "Exit code: {}\n"
                "Command:\n{}\n"
                "stdout:\n{}\n"
                "stderr:\n{}\n".format(proc.returncode, cmd_str, out, err)
            )
        return out
