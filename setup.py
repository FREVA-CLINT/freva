#!/usr/bin/env python
from __future__ import annotations
from pathlib import Path
from setuptools import setup, find_packages
import sys
from typing import List, Tuple
from tempfile import TemporaryDirectory
from deploy import find_version, read


COMMANDS = ["databrowser", "esgf", "history", "plugin", "crawl-my-data"]
this_dir = Path(__file__).parent
COMPLETION_DIR = this_dir / "assets" / "completions"
data_files = [
    (
        "freva",
        [
            str(this_dir / "assets" / "drs_config.toml"),
        ],
    )
]

def prep_tcsh_completion(tempdir: Path) -> list[tuple[str, list[str]]]:
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


def gather_completion_scripts(tempdir: Path) -> list[tuple[str, list[str]]]:
    """Gather all data_files related to shell completion scripts."""

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

with TemporaryDirectory(dir=COMPLETION_DIR) as td:
    data_files += gather_completion_scripts(Path(td))
    entry_points = ["freva = freva.cli:main"]
    for cmd in COMMANDS:
        entry_points.append(f"freva-{cmd} = freva.cli.{cmd.replace('-', '_')}:main")
    setup(
        name="evaluation_system",
        version=find_version("src/evaluation_system", "__init__.py"),
        author="German Climate Computing Centre (DKRZ)",
        maintainer="Climate Informatics and Technology (CLINT)",
        description="Free Evaluation and Analysis Framework (Freva) ",
        long_description=read("README.md"),
        long_description_content_type="text/markdown",
        license="BSD-3-Clause",
        packages=find_packages("src"),
        package_dir={"": "src"},
        data_files=data_files,
        install_requires=[
            "Django",
            "humanize",
            "mysqlclient",
            "numpy",
            "python-git",
            "pymysql",
            "pandas",
            "Pillow",
            "PyPDF2",
            "toml",
        ],
        extras_require={
            "docs": [
                "sphinx",
                "nbsphinx",
                "recommonmark",
                "ipython",  # For nbsphinx syntax highlighting
                "sphinxcontrib_github_alt",
            ],
            "test": [
                "pytest",
                "nbformat",
                "black",
                "pytest-html",
                "pytest-env",
                "pytest-cov",
                "nbval",
                "h5netcdf",
                "mock",
                "mypy",
                "requests_mock",
                "allure-pytest",
                "python-swiftclient",
                "testpath",
                "types-toml",
                "types-mock",
                "types-requests",
            ],
        },
        entry_points={"console_scripts": entry_points},
        python_requires=">=3.8",
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Environment :: Console",
            "Intended Audience :: Developers",
            "Intended Audience :: Science/Research",
            "License :: OSI Approved :: BSD License",
            "Operating System :: POSIX :: Linux",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Topic :: Scientific/Engineering :: Data Analysis",
            "Topic :: Scientific/Engineering :: Earth Sciences",
        ],
    )
