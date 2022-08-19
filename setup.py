#!/usr/bin/env python

from pathlib import Path
from setuptools.command.install import install
from setuptools import setup, find_packages
import shutil
import sys
from tempfile import TemporaryDirectory

from deploy import find_version, read, Installer, get_data_dirs


COMMANDS = ["databrowser", "esgf", "history", "plugin", "user-data"]
this_dir = Path(__file__).parent
COMPLETION_DIR = this_dir / "assets" / "completions"


def prep_tcsh_completion(tempdir):
    """Create completion scripts for tcsh."""

    script_dir = COMPLETION_DIR.relative_to(this_dir) / "tcsh"
    completion_helper = (
        Path(sys.prefix)
        / "share"
        / "tcsh-completion"
        / "helpers"
        / "tcsh-completion.bash"
    )
    script_paths = [
        (
            str(Path("share") / "tcsh-completion" / "helpers"),
            [str(script_dir / f"{completion_helper.name}")],
        ),
        (
            str(Path("share") / "tcsh-completion" / "completion"),
            [str(tempdir.relative_to(this_dir) / "freva")],
        ),
    ]
    completion_script = [
        "set autoexpand",
        f"complete freva 'p,*,`bash {completion_helper} \"${{COMMAND_LINE}}\"`,'",
    ]
    for cmd in COMMANDS:
        completion_script.append(
            f"complete {cmd} 'p,*,`bash {completion_helper} \"${{COMMAND_LINE}}\"`,'"
        )
    with (tempdir / "freva").open("w") as f:
        f.write("\n".join(completion_script))
    return script_paths


def gather_completion_scripts(tempdir):
    """Gather all data_files related to shell completion scripts."""

    # prefix = get_data_dirs(sys.prefix
    shells = {
        "zsh": Path("share") / "zsh" / "site-functions",
        "bash": Path("share") / "bash-completion" / "completions",
        "fish": Path("share") / "fish" / "completions",
    }
    data_files = []
    for shell, target_path in shells.items():
        comp_files = [
            str(f.relative_to(this_dir)) for f in (COMPLETION_DIR / shell).rglob("*")
        ]
        data_files.append((str(target_path), comp_files))
    return data_files + prep_tcsh_completion(tempdir)


class InstallCommand(install):
    """Customized setuptools install command."""

    def run(self):
        install.run(self)
        config_dir, data_dir, _ = get_data_dirs(self.prefix, self.user)
        with TemporaryDirectory(dir=COMPLETION_DIR) as td:
            data_files = gather_completion_scripts(Path(td))
            for target_dir, sources in data_files:
                full_target_dir = data_dir / target_dir
                for source in sources:
                    full_source = full_target_dir / Path(source).name
                    full_source.parent.mkdir(exist_ok=True, parents=True)
                    with full_source.open("w") as target_file:
                        with open(source, "r") as source_file:
                            target_file.write(source_file.read())
        if not (config_dir / "drs_config.toml").exists():
            shutil.copy(
                str(this_dir / "assets" / "drs_config.toml"),
                str(config_dir / "drs_config.toml"),
            )
        Installer.create_loadscript(self.prefix, bool(self.user))


def get_data_files():
    this_dir = Path(__file__).parent
    asset_dir = this_dir / "assets"
    dirs = [d for d in asset_dir.rglob("*") if d.is_dir()]
    files = []
    for d in dirs:
        target_dir = d.relative_to(this_dir)
        add_files = [str(f.relative_to(this_dir)) for f in d.rglob("*") if f.is_file()]
        if add_files:
            files.append((str(target_dir), add_files))
    files.append(("", ["deploy.py"]))
    return files


entry_points = ["freva = freva.cli:main"]
for cmd in COMMANDS:
    entry_points.append(f"freva-{cmd} = freva.cli.{cmd.replace('-', '_')}:main")
setup(
    name="freva",
    version=find_version("src/evaluation_system", "__init__.py"),
    author="German Climate Computing Centre (DKRZ)",
    maintainer="Climate Informatics and Technology (CLINT)",
    description="Free Evaluation and Analysis Framework (Freva) ",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    include_package_data=True,
    license="BSD-3-Clause",
    packages=find_packages("src"),
    package_dir={"": "src"},
    cmdclass={"install": InstallCommand},
    install_requires=[
        "appdirs",
        "GitPython",
        "dask",
        "Django",
        "humanize",
        "h5netcdf",
        "lazy-import",
        "mysqlclient",
        "netCDF4",
        "numpy",
        "pymysql",
        "pandas",
        "Pillow",
        "PyPDF2!=2.10.1",
        "requests",
        "toml",
        "toolz",
        "typing_extensions",
        "xarray",
    ],
    setup_requires=["appdirs"],
    extras_require={
        "docs": [
            "cartopy",
            "cftime",
            "cf_xarray",
            "ipython",
            "nbsphinx",
            "pint",
            "pint-xarray",
            "recommonmark",
            "sphinx",
            "sphinxcontrib_github_alt",
            "sphinx-execute-code-python3",
            "sphinx-rtd-theme",
            "xarray",
            "h5netcdf",
        ],
        "test": [
            "allure-pytest",
            "black",
            "django-stubs",
            "django-stubs-ext",
            "h5netcdf",
            "mock",
            "mypy",
            "nbval",
            "nbformat",
            "pep257",
            "pytest",
            "pytest-html",
            "pytest-env",
            "pytest-cov",
            "python-swiftclient",
            "requests_mock",
            "testpath",
            "types-mock",
            "types-requests",
            "types-toml",
            "types-urllib3",
            "types-toml",
            "types-requests",
        ],
    },
    entry_points={"console_scripts": entry_points},
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
    ],
)
