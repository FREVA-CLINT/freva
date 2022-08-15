"""Deploy the evaluation_system / core."""
import argparse
from configparser import ConfigParser, ExtendedInterpolation
import logging
import hashlib
import os
from os import path as osp
from pathlib import Path
import shlex
import sys
from subprocess import CalledProcessError, PIPE, run
import urllib.request
from tempfile import TemporaryDirectory

DEFAULT_PYTHON = "3.10"
MINICONDA_URL = "https://repo.anaconda.com/miniconda/"
ANACONDA_URL = "https://repo.anaconda.com/archive/"
CONDA_PREFIX = os.environ.get("CONDA", "Anaconda3-2022.05")
CONDA_VERSION = "{conda_prefix}-{arch}.sh"

logging.basicConfig(format="%(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__file__)

MODULE = """#%Module4.0 #######################################################
##
## FREVA - Free Evaluation System Framework modulefile
##
#
### BEGIN of config part ********
#define some variables
set shell [module-info shelltype]
set curMode [module-info mode]
module-whatis   "evaluation_system {version}"
proc ModulesHelp {{ }} {{
    puts stderr "Load the free evaluation system framework {project}"
}}
if {{ $curMode eq "load" }} {{
    if {{ $shell == "fish" }} {{
        puts "source {eval_conf_file.parent}/completions/complete_fish"
    }} elseif {{ $shell == "csh" }} {{
        puts "source {eval_conf_file.parent}/completions/complete_csh"
    }} elseif {{ $shell == "sh" }} {{
        puts ". {eval_conf_file.parent}/completions/complete_sh"
    }}
}}
prepend-path PATH {root_dir}/bin
setenv EVALUATION_SYSTEM_CONFIG_FILE {eval_conf_dir}/evaluation_system.conf
setenv EVALUATION_SYSTEM_CONFIG_DIR {eval_conf_dir}
"""

FISH_SCRIPT = """set -g EVALUATION_SYSTEM_CONFIG_FILE {eval_conf_dir}/evaluation_system.conf
set -g EVALUATION_SYSTEM_CONFIG_DIR {eval_conf_dir}
set -gx PATH {root_dir}/bin $PATH
{completion}
"""
FISH_COMPLETION = """source {root_dir}/share/fish/completions/freva.fish
"""

SH_SCRIPT = """export EVALUATION_SYSTEM_CONFIG_FILE={eval_conf_dir}/evaluation_system.config
export EVALUATION_SYSTEM_CONFIG_DIR={eval_conf_dir}
export PATH={root_dir}/bin:$PATH
shell=$(basename $SHELL)
{completion}
"""


SH_COMPLETION = """if [ -z "$shell" ];then
    shell=$(basename $SHELL)
fi
if [ $shell = zsh ];then
    source {root_dir}/share/zsh/site-functions/source.zsh
elif [ $shell = bash ];then
    source {root_dir}/share/bash-completion/completions/freva
fi
"""

CSH_SCRIPT = """setenv PATH {root_dir}/bin\:$PATH
setenv EVALUATION_SYSTEM_CONFIG_FILE "{eval_conf_dir}/evaluation_system.conf"
setenv EVALUATION_SYSTEM_CONFIG_DIR "{eval_conf_dir}"
{completion}
"""


CSH_COMPLETION = """if ( `basename $SHELL` == tcsh ) then
    source {root_dir}/share/tcsh-completion/completion/freva
endif
"""


def get_data_dirs(install_prefix, user):

    install_prefix = Path(install_prefix or sys.prefix)
    if user:
        import appdirs

        data_dir = Path(appdirs.user_data_dir()).parent
        root_dir = Path(appdirs.user_data_dir())
        config_dir = Path(appdirs.user_config_dir()) / "freva"
    else:
        root_dir = data_dir = Path(install_prefix)
        config_dir = root_dir / "freva"
    config_dir.mkdir(exist_ok=True, parents=True)
    return config_dir, data_dir, root_dir


def get_script_path():
    return osp.dirname(osp.realpath(sys.argv[0]))


def read(*parts):
    return open(osp.join(get_script_path(), *parts)).read()


def find_files(path, glob_pattern="*"):
    return [str(f) for f in Path(path).rglob(glob_pattern)]


def find_version(*parts):

    vers_file = read(*parts)
    old_path = sys.path.copy()
    with TemporaryDirectory() as td:
        with open(osp.join(td, "tmp_frevaversion.py"), "w") as f:
            f.write(vers_file)
        sys.path.insert(0, td)
        try:
            from tmp_frevaversion import __version__

            sys.path = old_path
            return __version__
        except ImportError:
            sys.path = old_path
    raise RuntimeError("Unable to find version string.")


def reporthook(count, block_size, total_size):
    if count == 0:
        return
    frac = count * block_size / total_size
    percent = int(100 * frac)
    bar = "#" * int(frac * 40)
    msg = "Downloading: [{0:<{1}}] | {2}% Completed".format(bar, 40, round(percent, 2))
    print(msg, end="\r", flush=True)
    if frac >= 1:
        print()


def parse_args(argv=None):
    """Consturct command line argument parser."""

    ap = argparse.ArgumentParser(
        prog="deploy_freva",
        description="""This Programm installs the evaluation_system package.""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument(
        "install_prefix", type=Path, help="Install prefix for the environment."
    )
    ap.add_argument(
        "--packages",
        type=str,
        nargs="*",
        help="Pacakges that are installed",
        default=[],
    )
    ap.add_argument(
        "--channel", type=str, default="conda-forge", help="Conda channel to be used"
    )
    ap.add_argument("--shell", type=str, default="bash", help="Shell type")
    ap.add_argument(
        "--arch",
        type=str,
        default="Linux-x86_64",
        choices=[
            "Linux-aarch64",
            "Linux-ppc64le",
            "Linux-s390x",
            "Linux-x86_64",
            "MacOSX-x86_64",
        ],
        help="Choose the architecture according to the system",
    )
    ap.add_argument(
        "--no_conda",
        "--no-conda",
        action="store_true",
        default=False,
        help="Do not create conda environment",
    )
    ap.add_argument(
        "--run_tests",
        action="store_true",
        default=False,
        help="Run unittests after installation",
    )
    ap.add_argument(
        "--editable",
        "-e",
        action="store_true",
        default=False,
        help="Apply pip install in editable mode.",
    )

    ap.add_argument(
        "--silent",
        "-s",
        action="store_true",
        default=False,
        help="Minimize writing to stdout",
    )
    args = ap.parse_args()
    return args


class Installer:
    @property
    def conda_name(self):

        return self.install_prefix.name

    def run_cmd(self, cmd, **kwargs):
        """Run a given command."""
        verbose = kwargs.pop("verbose", False)
        kwargs["check"] = False
        if self.silent and not verbose:
            kwargs["stdout"] = PIPE
            kwargs["stderr"] = PIPE
        res = run(shlex.split(cmd), **kwargs)
        if res.returncode != 0:
            try:
                print(res.stderr.decode())
            except AttributeError:
                # stderr wasn't piped
                pass
            raise CalledProcessError(res.returncode, cmd)

    def use_or_download_temp_conda(self, tempdir):
        """Return to path an existing conda env, if there is none, cerate one."""

        conda_exec_path = Path(os.environ.get("CONDA_EXEC_PATH", ""))
        if conda_exec_path.exists() and conda_exec_path.is_file():
            return Path(conda_exec_path)
        tmp_env = Path(tempdir) / "env"
        conda_script = Path(tempdir) / "anaconda.sh"
        logger.info(f"Downloading {CONDA_PREFIX} script")
        kwargs = {"filename": str(conda_script)}
        if self.silent is False:
            kwargs["reporthook"] = reporthook
        urllib.request.urlretrieve(
            self.conda_url
            + CONDA_VERSION.format(arch=self.arch, conda_prefix=CONDA_PREFIX),
            **kwargs,
        )
        self.check_hash(conda_script)
        conda_script.touch(0o755)
        cmd = f"{self.shell} {conda_script} -p {tmp_env} -b -f"
        logger.info(f"Installing {CONDA_PREFIX}:\n{cmd}")
        self.run_cmd(cmd)
        return tmp_env / "bin" / "conda"

    def create_conda(self):
        """Create the conda environment."""
        with TemporaryDirectory(prefix="conda") as td:
            conda_exec_path = self.use_or_download_temp_conda(td)
            cmd = f"{conda_exec_path} {self.create_command(td)}"
            logger.info(f"Creating conda environment:\n{cmd}")
            self.run_cmd(cmd)

    def create_command(self, tmp_dir):
        """Construct the conda create command."""
        # If packages were given, create a conda env from this packages list
        if not self.python:
            version_str = ""
        elif self.python[0] in "<=>":
            version_str = self.python
        else:
            version_str = f"={self.python}"
        if self.packages:
            packages = set(self.packages + ["conda", "pip"])
            return (
                f"create -c {self.channel} -q -p {self.install_prefix} "
                f"python{version_str} " + " ".join(packages) + " -y"
            )
        # This is awkward, but since we can't guarrantee that we have a yml
        # parser installed we have to do this manually
        env_file = Path(__file__).parent / "dev-environment.yml"
        return f"env create -q -p {self.install_prefix} -f {env_file} --force"

    def check_hash(self, filename):
        archive = urllib.request.urlopen(self.conda_url).read().decode()
        md5sum = ""
        for line in archive.split("</tr>"):
            if CONDA_VERSION.format(arch=self.arch, conda_prefix=CONDA_PREFIX) in line:
                md5sum = line.split("<td>")[-1].strip().strip("</td>")
        md5_hash = hashlib.md5()
        with filename.open("rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                md5_hash.update(byte_block)
        if md5_hash.hexdigest() != md5sum:
            raise ValueError("Download failed, md5sum mismatch: {md5sum} ")

    def pip_install(self, editable=False):
        """Install additional packages using pip."""

        if editable:
            cmd = f"{self.python_prefix} -m pip install -e .[test]"
        else:
            cmd = f"{self.python_prefix} -m pip install .[test]"
        logger.info(f"Installing additional packages\n{cmd}")
        self.run_cmd(cmd)

    def __init__(
        self,
        install_prefix,
        no_conda=False,
        packages=[],
        channel="conda-forge",
        shell="bash",
        arch="Linux-x86_64",
        python="3.10",
        run_tests=False,
        silent=False,
    ):
        self.run_tests = run_tests
        self.install_prefix: Path = Path(install_prefix).expanduser().absolute()
        self.packages = packages
        self.channel = channel
        self.arch = arch
        self.python = python
        self.silent = silent
        self.shell = shell
        if self.silent:
            logger.setLevel(logging.ERROR)
        self.conda_url = ANACONDA_URL
        if "miniconda" in CONDA_PREFIX.lower():
            self.conda_url = MINICONDA_URL
        self.conda = no_conda is False

    @staticmethod
    def create_paths_for_config(install_prefix, user):
        """Get and prepare the evaluation_system config file."""

        config_parser = ConfigParser(interpolation=ExtendedInterpolation())
        asset_conf_file = Path(__file__).parent / "assets" / "evaluation_system.conf"
        eval_conf_file = Path(
            os.environ.get("EVALUATION_SYSTEM_CONFIG_FILE", asset_conf_file)
        )
        with eval_conf_file.open("r") as fp:
            config_parser.read_file(fp)
        config_dir, data_dir, root_dir = get_data_dirs(install_prefix, user)
        if not config_parser["evaluation_system"]["root_dir"]:
            config_parser.set("evaluation_system", "root_dir", str(root_dir))
        if eval_conf_file == asset_conf_file:
            with asset_conf_file.open() as fobj:
                tmp_cfg = []
                for line in fobj.readlines():
                    if line.strip().startswith("root_dir"):
                        tmp_cfg.append(f"root_dir={root_dir}\n")
                    else:
                        tmp_cfg.append(line)
            eval_conf_file = config_dir / "evaluation_system.conf"
            if not eval_conf_file.exists():
                with open(eval_conf_file, "w") as fobj:
                    fobj.write("".join(tmp_cfg))
        for key in (
            "preview_path",
            "project_data",
            "base_dir_location",
            "scheduler_output_dir",
        ):
            path = Path(config_parser["evaluation_system"][key])
            if path:
                try:
                    path.mkdir(exist_ok=True, parents=True)
                except PermissionError:
                    logger.warning(f"Could not create path: {path}")
        return eval_conf_file, data_dir

    @staticmethod
    def create_loadscript(install_prefix, user=False):
        """Create the load-script for this installation."""
        config_parser = ConfigParser(interpolation=ExtendedInterpolation())
        install_prefix = Path(install_prefix or sys.prefix)
        eval_conf_file, root_dir = Installer.create_paths_for_config(
            install_prefix, user=user
        )
        with eval_conf_file.open("r") as fp:
            config_parser.read_file(fp)
        shell_scripts = dict(fish=FISH_SCRIPT, csh=CSH_SCRIPT, sh=SH_SCRIPT)
        completions = dict(fish=FISH_COMPLETION, csh=CSH_COMPLETION, sh=SH_COMPLETION)
        for shell in ("fish", "csh", "sh"):
            activate_file = eval_conf_file.parent / f"activate_{shell}"
            source_file = eval_conf_file.parent / "completions" / f"complete_{shell}"
            try:
                source_file.parent.mkdir(parents=True, exist_ok=True)
                with (activate_file).open("w") as f:
                    f.write(
                        shell_scripts[shell].format(
                            root_dir=install_prefix,
                            eval_conf_dir=eval_conf_file.parent,
                            completion=completions[shell].format(root_dir=root_dir),
                        )
                    )
                with (source_file).open("w") as f:
                    f.write(completions[shell].format(root_dir=install_prefix))
            except Exception as error:
                logging.warning("Could not create loadscripts: %s", str(error))
        try:
            with (eval_conf_file.parent / "loadfreva.modules").open("w") as f:
                f.write(
                    MODULE.format(
                        version=find_version("src/evaluation_system", "__init__.py"),
                        root_dir=install_prefix,
                        eval_conf_dir=eval_conf_file.parent,
                        project=config_parser["evaluation_system"]["project_name"],
                    )
                )
        except Exception as error:
            logging.warning("Could not create modulefile: %s", str(error))

    def unittests(self):
        """Run unittests."""
        logger.info("Running unittests:")
        env = os.environ.copy()
        env["PATH"] = f'{self.install_prefix / "bin"}:{env["PATH"]}'
        env["FREVA_ENV"] = str(self.install_prefix / "bin")
        self.run_cmd("make test", verbose=True, env=env)

    @property
    def python_prefix(self):
        """Get the path of the new conda evnironment."""
        return self.install_prefix / "bin" / "python3"


if __name__ == "__main__":
    args = parse_args(sys.argv)
    Inst = Installer(
        install_prefix=args.install_prefix,
        no_conda=args.no_conda,
        packages=args.packages,
        channel=args.channel,
        shell=args.shell,
        arch=args.arch,
        python=os.environ.get("PYTHON_VERSION", DEFAULT_PYTHON),
        run_tests=args.run_tests,
        silent=args.silent,
    )
    if Inst.conda:
        Inst.create_conda()
        if "freva" not in args.packages:
            Inst.pip_install(args.editable)
    Inst.create_loadscript(Inst.install_prefix)
    if Inst.run_tests:
        Inst.unittests()
