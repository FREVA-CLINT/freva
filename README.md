# Free Evaluation System Framework for Earth System Modeling

## INFO:

This is the BETA version of the Freva framework. Goto freva.met.fu-berlin.de, click on 'Guest?', login, and browse the evaluation system at the Freie Universität Berlin (GERMANY).

You can play with a test version on binder [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/git/https%3A%2F%2Fgitlab.dkrz.de%2Ffreva%2Fevaluation_system.git/freva-dev)

### What is Freva?

Freva is an all-in-one solution to efficiently handle evaluation and validation systems of research projects, institutes or universities in the Earth system and climate modeling community. It is a hybrid scientific software framework for high performance computing, including all features present in the shell and web environment. The main system design features the common and standardized model database, programming interface, and history of evaluations. The database interface satisfies the international data standards provided by the Earth System Grid Federation and the World Climate Research Programm. Freva indexes different data projects into one common search environment by storing the meta data information of the model, reanalysis and observational data sets in a database. This implemented meta data system with its advanced but easy-to-handle search tool supports at different stages: users, developers and their plugins to retrieve the required information of the database. A generic application programming interface allows scientific developers to connect their analysis tools with the evaluation system independently of the programming language used. Users of the evaluation techniques benefit from the common interface of the evaluation system without any need to understand the different scripting languages. The history and configuration sub-system stores every analysis performed with the evaluation system in a database. Configurations and results of the tools can be shared among scientists via shell or web system. Results of plugged-in tools benefit from scientific transparency and reproducibility within the research group. Furthermore, if saved configurations match while starting an evaluation plugin, the system suggests to use results already produced by other users – saving CPU/h, I/O, disk space and time. The efficient interaction between different technologies improves the Earth system modeling science.

## Guides:

Find details for users, developers, and admins of Freva in the guides.

https://github.com/FREVA-CLINT/Freva/tree/master/docu/guides

## Deployment (with python distribution):

Since version 2021.5 `evaluation_system` backend and command line interface
is deployed via a dedicated deploy repository. This deployment routine sets up
the backend, frontend and all services. To deploy the system in production
mode use the [deployment repository](https://gitlab.dkrz.de/freva/deployment).

## Setting up local development system:

A basic local development setup can be created using [Docker](https://docs.docker.com/engine/install/) and
[`docker-compose`](https://docs.docker.com/compose/install/) (Linux users need to install it separately). This also
requires that the `.envrc` file is sourced.

```
source .envrc
docker-compose up -d
```

Dummy data can be injected into a running `docker-compose` environment with `make dummy-data`. This will add some DRS
files into Solr and run an example plugin a few times to add some history data.

_Note_: MariaDB and Solr will listen on ports 10000 and 10001 respectively to avoid collisions if these are already
running on the machine.

When finished, tear down the environment with

```
docker-compose down
```

### Creating a dedicated anaconda dev environment
We recommend using anaconda to install all packages that are needed for
development of both backend and web frontend. Here we assume that you have a
working anaconda version per-installed on your local computer. To install the
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
_Note_: The conda install command can be slow. If you want to speed up the installation
        of the environment we recommend to install the `mamba` package in the
        anaconda `base` environment and use the `mamba` command to create the environment:
```
conda install mamba
mamba env create -f dev-environment.yml
source .envrc
```

### Installing the python package

Use the `pip install` command to install the actual python core packages into your activated environment:

```bash
pip install -e .[test]
```

The `-e` flag will link the source code into your python environment, which can be useful for development purpose.

### Running tests and creating a test coverage report

The system can be tested with a `Makefile`. To run the tests and generate a simple test coverage report simply use the make command:

```bash
make test
```

The linter testing can be applied by:

```bash
make lint
```

## Central configuration

The default configuration is located in `install_prefx/etc/evaluation_system.conf`.
Here you should set the entries pointing to the mysql database and the apache solr server.

> **_Note:_** Since version 2021.5 the config files can take variables that can be reused within the config file, see https://docs.python.org/3/library/configparser.html#configparser.ExtendedInterpolation for details.
Configurations containing the '$' character must be escaped by '$$' (additional $) to avoid conflicts.

### The module file

The deployment process will create a module file, which is located in `install_prefix/share/loadfreva.modules`. Copy this file to the appropriate location of your central modules system to make use of it.