#!/usr/bin/env python3
import argparse
import logging
import hashlib
from pathlib import Path
import shlex
import stat
from subprocess import (CalledProcessError, PIPE, run)
import urllib.request
from tempfile import NamedTemporaryFile, TemporaryDirectory
import time


SHASUM='1314b90489f154602fd794accfc90446111514a5a72fe1f71ab83e07de9504a7'
CONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"

logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__file__)

def reporthook(count, block_size, total_size):
    global start_time
    if count == 0:
        start_time = time.time()
        return
    elapsed = time.time() - start_time
    progress_size = int(count * block_size)
    speed = int(progress_size / (1024 * elapsed))
    frac = count * block_size / total_size
    percent = int(100 * frac)
    bar = '#' * int(frac * 40)
    msg = "\rDownloading: [{0:<{1}}] | {2}% Completed".format(
           bar, 40, round(percent, 2))
    sys.stdout.write(msg)
    sys.stdout.flush()


def parse_args(argv=None):
    """Consturct command line argument parser."""

    ap = argparse.ArgumentParser(prog='install_freva',
            description="""This Programm sets up a conda environment for jupyter on mistral""", formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ap.add_argument('install_prefix', type=Path,
                    help='Install prefix for the environment.')
    ap.add_argument('--packages', type=str, nargs='*',
            help='Pacakges that are installed', default=Installer.default_pkgs)
    ap.add_argument('--channel', type=str, default='conda-forge', help='Conda channel to be used')
    ap.add_argument('--shell', type=str, default='bash',
                    help='Shell type')
    ap.add_argument('--python', type=str, default='3.9',
            help='Python Version')
    ap.add_argument('--pip', type=str, nargs='*', default=Installer.pip_pkgs,
            help='Additional packages that should be installed using pip')
    ap.add_argument('--develop', action='store_true' default=False,
            help='Use the develop flag when installing the evaluation_system package')
    args = ap.parse_args()
    return args



class Installer:


    default_pkgs = sorted(['cdo', 'conda', 'configparser',
                    'django', 'ffmpeg', 'git', 'gitpython',
                    'ipython', 'imagemagick', 'libnetcdf',
                    'mysqlclient', 'nco', 'netcdf4', 'numpy', 'pip',
                    'pymysql', 'pypdf2', 'pytest', 'pytest-env',
                    'pytest-cov', 'pytest-html', 'python-cdo', 'xarray'])
    pip_pkgs = sorted(['pytest-html', 'python-git', 'python-swiftclient'])

    @property
    def conda_name(self):

        return self.install_prefix.name

    @staticmethod
    def run_cmd(cmd, **kwargs):
        """Run a given command."""

        res = os.system(cmd)
        if res != 0:
            raise CalledProcessError(res, cmd)

    def create_conda(self):
        """Create the conda environment."""

        with TemporaryDirectory(prefix='conda') as td:
            conda_script = Path(td) /'miniconda.sh'
            tmp_env = Path(td) / 'env'
            logger.info('Downloading miniconda script')
            urllib.request.urlretrieve(CONDA_URL,
                                      filename=str(conda_script),
                                      reporthook=reporthook)
            print()
            self.check_hash(conda_script)
            conda_script.touch(0o755)
            cmd = f"{self.shell} {conda_script} -p {tmp_env} -b -f -u"
            logger.info(f'Installing miniconda:\n\t{cmd}')
            self.run_cmd(cmd)
            cmd = f"{tmp_env / 'bin' / 'conda'} create -c {self.channel} -q -p {self.install_prefix} python={self.python} {' '.join(self.packages)} -y"
            logger.info(f'Creating conda environment:\n\t {cmd}')
            self.run_cmd(cmd)

    @staticmethod
    def check_hash(filename):
        sha256_hash = hashlib.sha256()
        with filename.open('rb') as f:
            for byte_block in iter(lambda: f.read(4096),b""):
                sha256_hash.update(byte_block)
        if sha256_hash.hexdigest() != SHASUM:
            raise ValueError('Download failed, shasum mismatch')

    def pip_install(self):
        """Install additional packages using pip."""

        cmd = f"{self.python_prefix} -m pip install {' '.join(self.pip)}"
        logger.info(f'Installing additional packages\n\t {cmd}')
        self.run_cmd(cmd)
        pip_opts = ''
        if self.develop:
            pip_opts = '-e'
        cmd = f"{self.python_prefix} -m pip install {pip_opts} ."
        logger.info('Installing evaluation_system packages')
        self.run(cmd)

    def __init__(self, args):

        self._python_prefix = None #self.prefix / 'python'
        for arg in vars(args):
            setattr(self, arg, getattr(args,arg))
        self.install_prefix = self.install_prefix.expanduser().absolute()
        self.install_prefix.mkdir(exist_ok=True, parents=True)
        if not 'flit' in self.packages:
            self.packages.append('flit')

    @property
    def conda_prefix(self):
        return Path(context.conda_prefix)

    @property
    def python_prefix(self):
        """Get the path of the new conda evnironment."""
        return self.install_prefix / 'bin' / 'python3'
if __name__ == '__main__':
    import sys, os
    
    args = parse_args(sys.argv)
    Inst = Installer(args)
    #Inst.create_conda()
    Inst.pip_install()

