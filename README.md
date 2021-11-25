# Free Evaluation System Framework for Earth System Modeling

## INFO:

This is the BETA version of the Freva framework. Goto freva.met.fu-berlin.de, click on 'Guest?', login, and browse the evaluation system at the Freie Universität Berlin (GERMANY).

You can play with a test version on binder [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/git/https%3A%2F%2Fgitlab.dkrz.de%2Ffreva%2Fevaluation_system.git/freva-dev)

### What is Freva?

Freva is an all-in-one solution to efficiently handle evaluation and validation systems of research projects, institutes or universities in the Earth system and climate modeling community. It is a hybrid scientific software framework for high performance computing, including all features present in the shell and web environment. The main system design features the common and standardized model database, programming interface, and history of evaluations. The database interface satisfies the international data standards provided by the Earth System Grid Federation and the World Climate Research Programme. Freva indexes different data projects into one common search environment by storing the meta data information of the model, reanalysis and observational data sets in a database. This implemented meta data system with its advanced but easy-to-handle search tool supports at different stages: users, developers and their plugins to retrieve the required information of the database. A generic application programming interface allows scientific developers to connect their analysis tools with the evaluation system independently of the programming language used. Users of the evaluation techniques benefit from the common interface of the evaluation system without any need to understand the different scripting languages. The history and configuration sub-system stores every analysis performed with the evaluation system in a database. Configurations and results of the tools can be shared among scientists via shell or web system. Results of plugged-in tools benefit from scientific transparency and reproducibility within the research group. Furthermore, if saved configurations match while starting an evaluation plugin, the system suggests to use results already produced by other users – saving CPU/h, I/O, disk space and time. The efficient interaction between different technologies improves the Earth system modeling science.

## Guides:

Find details for users, developers, and admins of Freva in the guides.

https://github.com/FREVA-CLINT/Freva/tree/master/docu/guides

## Deployment (with python distribution):

Since version 2021.5 there is `evaluation_system` package is deployed _within_
the python environment. No seperation between the two is needed. Here we assume
you want to deploy the code along with fresh python installation that should
located `install_prefix`. To deploy, that is install a fresh python distribution
and the `evaluation_system` package use the `deploy.py` script:

```bash
$: python deploy.py install_prefix
```

Additional fine tuning is possible via the following command line arguments:

```bash
usage: deploy_freva [-h] [--packages [PACKAGES [PACKAGES ...]]] [--channel CHANNEL] [--shell SHELL] [--python PYTHON] [--pip [PIP [PIP ...]]] [--develop] [--no_conda] install_prefix

This Programm installs the evaluation_system package.

positional arguments:
  install_prefix        Install prefix for the environment.
optional arguments:
  -h, --help            show this help message and exit
  --packages [PACKAGES ...]
                        Pacakges that are installed (default: ['cartopy', 'cdo', 'conda',
                        'configparser', 'dask', 'distributed', 'django', 'ffmpeg', 'git', 'gitpython',
                        'humanize', 'imagemagick', 'ipython', 'libnetcdf', 'mysqlclient', 'nco',
                        'netcdf4', 'numpy', 'pandas', 'pandoc', 'pillow', 'pip', 'pymysql', 'pypdf2',
                        'pytest', 'pytest-cov', 'pytest-env', 'pytest-html', 'python-cdo', 'xarray'])
  --channel CHANNEL     Conda channel to be used (default: conda-forge)
  --shell SHELL         Shell type (default: bash)
  --arch {Linux-aarch64,Linux-ppc64le,Linux-s390x,Linux-x86_64,MacOSX-x86_64}
                        Choose the architecture according to the system (default: Linux-x86_64)
  --python PYTHON       Python Version (default: 3.9)
  --pip [PIP ...]       Additional packages that should be installed using pip (default: ['pytest-
                        html', 'python-git', 'python-swiftclient'])
  --develop             Use the develop flag when installing the evaluation_system package (default:
                        False)
  --no_conda, --no-conda
                        Do not create conda environment (default: False)
  --run_tests           Run unittests after installation (default: False)
  --silent, -s          Minimize writing to stdout (default: False)
```

### Central configuration

The default configuration is located in `install_prefx/etc/evaluation_system.conf`.
Here you should set the entries pointing to the mysql database and the apache solr server.

> **_Note:_** Since version 2021.5 the config files can take variables that can be reused within the configfile, see https://docs.python.org/3/library/configparser.html#configparser.ExtendedInterpolation for details. Configurations containing the '$' charatcter must be escaped by '$$' (additional $) to avoid conflicts.

### The module file

The deployment process will create a module file, which is located in `install_prefix/share/loadfreva.modules`. Copy this file to the appropriate location of your central modules system to make use of it.

## Test/Development system

A basic local development setup can be created using [Docker](https://docs.docker.com/engine/install/) and
[`docker-compose`](https://docs.docker.com/compose/install/) (Linux users need to install it separately). This also
requires that the `.envrc` file is sourced.

```
source .envrc
docker-compose up -d
```

_Note_: MariaDB and Solr will listen on ports 10000 and 10001 respectively to avoid collisions if these are already
running on the machine.

When finished, tear down the environment with

```
docker-compose down
```

### Creating a dedicated anaconda dev environment
We recommend using anaconda to install all packages that are needed for
development of both backend and web frontend. Here we assume that you have a
working anaconda version pre-installed on your local computer. To install the
the dev environment simply use the following command:

```
conda env create -f dev-environment.yml
```
The freshly installed environment can be activated:
```
conda activate freva-dev
```
You can also save the above environment variables stored in `.envrc` upon activation of the conda environment:
```
source .envrc
conda env config vars set EVALUATION_SYSTEM_CONFIG_FILE=$EVALUATION_SYSTEM_CONFIG_FILE
conda env config vars set PUBKEY=$EVALUATION_SYSTEM_CONFIG_FILE
```
This will automatically set the above environment variables.

The conda environment can be deactivated using the following command:
```
conda deactivate
```

### Installing the python package

It is also possible to only install the python core packages. For example when installing the packe as part of a submodule. This can simply be done by the following command:

```bash
$: pip install (-e) .
```

This command will install the `evaluation_system` code into whatever python environment is activated. Use the `-e` flag for debugging.

## Running tests and uploading test coverage files

The system can be tested with `Makefile`. To run the tests and upload the coverage files simply use the make command:

```bash
$:  make all
```

If the `$FREVA_ENV` variable is not set `make` will take the current python environment.
