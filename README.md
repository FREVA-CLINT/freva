# Free Evaluation System Framework

[![PyPI version](https://badge.fury.io/py/freva.svg)](https://badge.fury.io/py/freva)
[![Update](https://anaconda.org/conda-forge/freva/badges/latest_release_date.svg)](https://github.com/FREVA-CLINT/freva)
[![Anaconda-Server Badge](https://anaconda.org/conda-forge/freva/badges/version.svg)](https://anaconda.org/conda-forge/freva)
[![Docs](https://img.shields.io/badge/Freva-Docs-green.svg)](https://freva-clint.github.io/freva)
[![codecov](https://codecov.io/gh/FREVA-CLINT/freva/branch/main/graph/badge.svg)](https://codecov.io/gh/FREVA-CLINT/freva)
[![Pipeline](https://github.com/FREVA-CLINT/freva/actions/workflows/ci_job.yml/badge.svg)](https://github.com/FREVA-CLINT/freva/actions)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/FREVA-CLINT/freva/main?labpath=Readme.ipynb)
[![BSD](https://anaconda.org/conda-forge/freva/badges/license.svg)](https://github.com/FREVA-CLINT/freva)

 > 💡 A new version of Freva is on the way! While it’s still under development,
   you can already start using it. If your primary focus is searching and
   accessing data, we highly recommend trying out the new Freva client
   (https://pypi.org/project/freva-client/)



<img src="docs/source/_static/freva_flowchart-new.jpg" alt="Freva" width="400"/>

## What is Freva ?
Freva, the free evaluation system framework, is a data search and analysis
platform developed by the atmospheric science community for the atmospheric
science community. With help of Freva researchers can:

- quickly and intuitively search for data stored at typical data centers that
  host many datasets.
- create a common interface for user defined data analysis tools.
- apply data analysis tools in a reproducible manner.

Data analysis is realised by user developed data analysis plugins. These plugins
are code agnostic, meaning that users don't have to rewrite the core of their
plugins to make them work with Freva. All that Freva does is providing a user
interface for the plugins.

Currently Freva comes in three different flavours:

- a python module that allows the usage of Freva in python environments, like
  jupyter notebooks
- a command line interface (cli) that allows using Freva from the command
  lines and shell scripts.
- a web user interface (web-ui)



## Where can I find the Freva user documentation?
A more detailed overview on the usage of freva can be found on the
[freva user documentation page](https://freva-clint.github.io/freva)



## How can I install Freva at my institution?

Deployment is realised via a dedicated repository that holds code to set up
the command line and web user interface as well as all services.
To deploy the system in production
mode consult [deployment docs](https://freva.gitlab-pages.dkrz.de/deployment/index.html).

## How can I set up a local version for development?

To start development with freva clone the repository and its submodules:

```
git clone --recursive https://github.com/FREVA-CLINT/freva.git
```

A basic local development setup can be created using
[Docker](https://docs.docker.com/engine/install/) and
[`docker-compose`](https://docs.docker.com/compose/install/)
(Linux users need to install it separately).

This also requires that the `.envrc` file is sourced.

```
docker-compose up -d
```

Dummy data can be injected into a running `docker-compose` environment with
`make dummy-data`. This will add some example files into solr and run an
example plugin a few times to add some history data.

When finished, tear down the environment with

```
docker-compose down
```

### Creating a dedicated anaconda dev environment
We recommend using anaconda to install all packages that are needed for
development. Here we assume that you have a
working anaconda version per-installed on your local computer. To install
the dev environment simply use the following command:

```
conda env create -f dev-environment.yml
source .envrc
```
This will automatically set environment variables needed for development.
The freshly installed environment can be activated:
```
conda activate freva-dev
```
The conda environment can be deactivated using the following command:
```
conda deactivate
```
_Note_: The conda install command can be slow. If you want to speed up the
installation of the environment we recommend to install the `mamba` package in
the anaconda `base` environment and use the `mamba` command to create the
environment:

```
conda install mamba
mamba env create -f dev-environment.yml
source .envrc
```

### Installing the python package

Use the `pip install` command to install the actual python core packages into
your activated environment:

```bash
pip install -e .[test]
```

The `-e` flag will link the source code into your python environment, which
can be useful for development purpose.

### Running tests and creating a test coverage report

The system can be tested with a `Makefile`. To run the tests and generate a
simple test coverage report simply use the make command:

```bash
make test
```

The linter testing can be applied by:

```bash
make lint
```

### Usage of pre-commit setup

To use the pre-commit setup in freva, follow these steps:

1. **Install Pre-commit**:
   - First, install the `pre-commit` package using pip:
     ```bash
     pip install pre-commit
     ```

2. **Activate Hooks**:
   - Navigate to the root directory of your repository and run the following command to set up the git hooks:
     ```bash
     pre-commit install
     ```

3. **Automatic Checks**:
   - Now, each time you attempt to commit changes, the pre-commit hooks will automatically run to ensure your files adhere to the specified standards.

4. **Manual Execution**:
   - If you want to manually run the hooks on all files, use:
     ```bash
     pre-commit run --all-files
     ```
