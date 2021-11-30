#!/usr/bin/env python3
import argparse
from configparser import ConfigParser, NoSectionError, ExtendedInterpolation
import logging
import hashlib
import os
from os import path as osp
from pathlib import Path
import re
import shlex
import sys
from subprocess import CalledProcessError, PIPE, run
import shutil
import urllib.request
from tempfile import NamedTemporaryFile, TemporaryDirectory


MINICONDA_URL = "https://repo.anaconda.com/miniconda/"
ANACONDA_URL = "https://repo.anaconda.com/archive/"
CONDA_PREFIX = os.environ.get("CONDA", "Anaconda3-2021.11")
CONDA_VERSION = "{conda_prefix}-{arch}.sh"

logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__file__)

MODULE='''#%Module1.0#####################################################################
##
## FREVA - Free Evaluation Framework modulefile
##
#
### BEGIN of config part ********
#define some variables
set shell [module-info shell]
set modName [module-info name]
set toolName evaluation_system
set curMode [module-info mode]
module-whatis   "evaluation_system {version}"
proc ModulesHelp {{ }} {{
    puts stderr "evaluation_system {version}"
}}
proc show_info {{}}  {{
    puts stderr {{
Freva command line
Available commands:
  --plugin       : Applies some analysis to the given data.
  --history      : provides access to the configuration history
  --databrowser  : Find data in the system
  --crawl_my_data: Use this command to update your projectdata.
  --esgf         : Browse ESGF data and create wget script

Usage: freva --COMMAND [OPTIONS]
To get help for the individual commands use
  freva --COMMAND --help
  }}
}}

#pre-requisites
if {{ $curMode eq "load" }} {{
	if {{ $shell == "bash" || $shell == "sh" }} {{
		        puts ". {auto_comp};"
			puts stderr "Evaluation System by Freva successfully loaded."
			puts stderr "If you are using bash, try the auto complete feature for freva and freva --databrowser
by hitting tab as usual."
			puts stderr "For more help/information check: "
			show_info
            }} else {{
		puts stderr "WARNING: Evaluation System is maybe NOT fully loaded, please type 'bash -l' "
		puts stderr "And load it again -> module load evaluation_system"
		puts stderr "Your shell now: $shell"
		}}
}} elseif {{ $curMode eq "remove" }} {{
	puts stderr "Evaluation System successfully unloaded."
}}
#only one version at a time!!
conflict evaluation_system
prepend-path PATH {path}
prepend-path LD_LIBRARY_PATH {ld_lib_path}
'''


def get_script_path():
    return osp.dirname(osp.realpath(sys.argv[0]))


def read(*parts):
    return open(osp.join(get_script_path(), *parts)).read()

def find_files(path, glob_pattern='*'):
    return [str(f) for f in Path(path).rglob(glob_pattern)]

def find_version(*parts):
    vers_file = read(*parts)
    match = re.search(r'^__version__ = "(\d+.\d+)"', vers_file, re.M)
    if match is not None:
        return match.group(1)
    raise RuntimeError("Unable to find version string.")



def reporthook(count, block_size, total_size):
    if count == 0:
        return
    frac = count * block_size / total_size
    percent = int(100 * frac)
    bar = '#' * int(frac * 40)
    msg = "Downloading: [{0:<{1}}] | {2}% Completed".format(
           bar, 40, round(percent, 2))
    print(msg, end='\r', flush=True)
    if frac >= 1:
        print()


def parse_args(argv=None):
    """Consturct command line argument parser."""

    ap = argparse.ArgumentParser(prog='deploy_freva',
            description="""This Programm installs the evaluation_system package.""",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ap.add_argument('install_prefix', type=Path,
                    help='Install prefix for the environment.')
    ap.add_argument('--packages', type=str, nargs='*',
            help='Pacakges that are installed', default=Installer.default_pkgs)
    ap.add_argument('--channel', type=str, default='conda-forge', help='Conda channel to be used')
    ap.add_argument('--shell', type=str, default='bash',
                    help='Shell type')
    ap.add_argument('--arch', type=str, default='Linux-x86_64',
                   choices=['Linux-aarch64', 'Linux-ppc64le', 'Linux-s390x',
                            'Linux-x86_64', 'MacOSX-x86_64'],
                   help='Choose the architecture according to the system')
    ap.add_argument('--python', type=str, default='3.9',
            help='Python Version')
    ap.add_argument('--pip', type=str, nargs='*', default=Installer.pip_pkgs,
            help='Additional packages that should be installed using pip')
    ap.add_argument('--develop', action='store_true', default=False,
            help='Use the develop flag when installing the evaluation_system package')
    ap.add_argument('--no_conda', '--no-conda', action='store_true', default=False,
            help='Do not create conda environment')
    ap.add_argument('--run_tests', action='store_true', default=False,
            help='Run unittests after installation')
    ap.add_argument('--silent', '-s', action='store_true', default=False,
            help='Minimize writing to stdout')
    args = ap.parse_args()
    return args



class Installer:


    default_pkgs = sorted(['cdo', 'conda', 'configparser', 'distributed',
                    'django', 'ffmpeg', 'git', 'gitpython', 'dask',
                    'ipython', 'imagemagick', 'libnetcdf', 'humanize', 'mamba',
                    'mysqlclient', 'nco', 'netcdf4', 'numpy', 'pandas', 'pip',
                    'pillow', 'pymysql', 'pypdf2', 'pytest', 'pytest-env', 'cartopy',
                    'pytest-cov', 'pytest-html', 'python-cdo', 'xarray', 'pandoc'])
    pip_pkgs = sorted(['pytest-html', 'python-git', 'python-swiftclient'])

    @property
    def conda_name(self):

        return self.install_prefix.name

    def run_cmd(self, cmd, **kwargs):
        """Run a given command."""
        verbose = kwargs.pop('verbose', False)
        kwargs['check'] = False
        if self.silent and not verbose:
            kwargs['stdout'] = PIPE
            kwargs['stderr'] = PIPE
        res = run(shlex.split(cmd), **kwargs)
        if res.returncode != 0:
            try:
                print(res.stderr.decode())
            except AttributeError:
                # stderr wasn't piped
                pass
            raise CalledProcessError(res.returncode, cmd)

    def create_conda(self):
        """Create the conda environment."""
        with TemporaryDirectory(prefix='conda') as td:
            conda_script = Path(td) / 'anaconda.sh'
            tmp_env = Path(td) / 'env'
            logger.info(f'Downloading {CONDA_PREFIX} script')
            kwargs = {'filename': str(conda_script)}
            print(self.arch)
            print(self.conda_url+CONDA_VERSION.format(arch=self.arch,
                                                      conda_prefix=CONDA_PREFIX))
            if  self.silent is False:
                kwargs['reporthook'] = reporthook
            urllib.request.urlretrieve(
                    self.conda_url+CONDA_VERSION.format(arch=self.arch,
                                                        conda_prefix=CONDA_PREFIX),
                    **kwargs
            )
            self.check_hash(conda_script)
            conda_script.touch(0o755)
            cmd = f"{self.shell} {conda_script} -p {tmp_env} -b -f"
            logger.info(f"Installing {CONDA_PREFIX}:\n{cmd}")
            self.run_cmd(cmd)
            cmd = f"{tmp_env / 'bin' / 'conda'} create -c {self.channel} -q -p {self.install_prefix} python={self.python} {' '.join(self.packages)} -y"
            logger.info(f'Creating conda environment:\n{cmd}')
            self.run_cmd(cmd)

    def check_hash(self, filename):
        archive = urllib.request.urlopen(self.conda_url).read().decode()
        md5sum = ''
        for line in archive.split('</tr>'):
            if CONDA_VERSION.format(arch=self.arch,
                                    conda_prefix=CONDA_PREFIX) in line:
                md5sum = line.split('<td>')[-1].strip().strip('</td>')
        md5_hash = hashlib.md5()
        with filename.open('rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                md5_hash.update(byte_block)
        if md5_hash.hexdigest() != md5sum:
            raise ValueError('Download failed, md5sum mismatch: {md5sum} ')

    def pip_install(self):
        """Install additional packages using pip."""

        cmd = f"{self.python_prefix} -m pip install .[test]"
        logger.info(f'Installing additional packages\n{cmd}')
        self.run_cmd(cmd)
        pip_opts = ''
        if self.develop:
            pip_opts = '-e'
        cmd = f"{self.python_prefix} -m pip install {pip_opts} ."
        logger.info('Installing evaluation_system packages')
        self.run_cmd(cmd)

    def __init__(self, args):

        for arg in vars(args):
            setattr(self, arg, getattr(args, arg))
        if self.silent:
            logger.setLevel(logging.ERROR)
        self.conda_url = ANACONDA_URL
        if 'miniconda' in CONDA_PREFIX.lower():
            self.conda_url = MINICONDA_URL
        self.install_prefix = self.install_prefix.expanduser().absolute()
        self.conda = self.no_conda == False

    def create_config(self):
        """Copy evaluation_system.conf to etc."""

        this_dir = Path(__file__).absolute().parent
        config_file = 'evaluation_system.conf'
        defaults = dict(root_dir=self.install_prefix,
                        base_dir_location=self.install_prefix / 'work',
                        base_dir='evaluation_system',
                        project_name='evaluation_system',)
        if not (this_dir / config_file).is_file():
            raise ValueError('No config file. Edit and copy the config template'
                             ' "evaluation_system.conf.tmpl" to '
                             '"evaluation_system.conf"')
        with (this_dir / config_file).open() as f:
            config = f.readlines()
        for nn, line in enumerate(config):
            cfg_key = line.split('=')[0].strip()
            if cfg_key in defaults:
                value = line.split('=')[-1].strip()
                if not value:
                    value = defaults[cfg_key]
                config[nn] = f'{cfg_key}={value}\n'
        (self.install_prefix / 'etc').mkdir(exist_ok=True, parents=True)
        with (self.install_prefix / 'etc' / config_file).open('w') as f:
            f.write(''.join(config))

    def create_auxilary(self, auxilary_dirs=('etc', 'sbin')):
        """Copy all auxilary files."""

        this_dir = Path(__file__).absolute().parent

        for d in auxilary_dirs:
            for source in (this_dir / d).rglob('*'):
                target = self.install_prefix / source.relative_to(this_dir)
                if source.is_file():
                    target.parent.mkdir(exist_ok=True, parents=True)
                    logger.info(f'Copying auxilary file {source}')
                    shutil.copy(source, target)
        config_parser = ConfigParser(interpolation=ExtendedInterpolation())
        for key in 'preview_path', 'project_data', 'base_dir_location', 'scheduler_output_dir':
            with open(self.install_prefix/ 'etc' / 'evaluation_system.conf', 'r') as fp:
                config_parser.read_file(fp)
                try:
                    Path(config_parser['evaluation_system'][key]).mkdir(exist_ok=True, parents=True)
                except PermissionError:
                    pass
        freva_path = self.install_prefix / 'share' / 'freva'
        freva_path.mkdir(parents=True, exist_ok=True)
        with (freva_path / 'loadfreva.modules').open('w') as f:
            f.write(MODULE.format(version=find_version('src/evaluation_system',
                                                       '__init__.py'),
                          path=self.install_prefix / 'bin',
                          ld_lib_path=self.install_prefix / 'lib',
                          auto_comp=self.install_prefix / 'etc' / 'autocomplete.bash'
                          ))


    def unittests(self):
        """Run unittests."""
        logger.info('Running unittests:')
        env = os.environ.copy()
        env['PATH'] = f'{self.install_prefix / "bin"}:{env["PATH"]}'
        env['FREVA_ENV'] = str(self.install_prefix / "bin")
        self.run_cmd(f'make test', verbose=True, env=env)

    @property
    def python_prefix(self):
        """Get the path of the new conda evnironment."""
        return self.install_prefix / 'bin' / 'python3'
if __name__ == '__main__':
    args = parse_args(sys.argv)
    Inst = Installer(args)
    if Inst.conda:
        Inst.create_conda()
        Inst.create_config()
        Inst.create_auxilary()
    Inst.pip_install()
    if Inst.run_tests:
        Inst.unittests()
