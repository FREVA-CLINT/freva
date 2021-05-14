
# Free Evaluation System Framework for Earth System Modeling

## INFO:
This is the BETA version of the Freva framework. Goto freva.met.fu-berlin.de, click on 'Guest?', login, and browse the evaluation system at the Freie Universität Berlin (GERMANY).

### What is Freva?
Freva is an all-in-one solution to efficiently handle evaluation and validation systems of research projects, institutes or universities in the Earth system and climate modeling community. It is a hybrid scientific software framework for high performance computing, including all features present in the shell and web environment. The main system design features the common and standardized model database, programming interface, and history of evaluations. The database interface satisfies the international data standards provided by the Earth System Grid Federation and the World Climate Research Programme. Freva indexes different data projects into one common search environment by storing the meta data information of the model, reanalysis and observational data sets in a database. This implemented meta data system with its advanced but easy-to-handle search tool supports at different stages: users, developers and their plugins to retrieve the required information of the database. A generic application programming interface allows scientific developers to connect their analysis tools with the evaluation system independently of the programming language used. Users of the evaluation techniques benefit from the common interface of the evaluation system without any need to understand the different scripting languages. The history and configuration sub-system stores every analysis performed with the evaluation system in a database. Configurations and results of the tools can be shared among scientists via shell or web system. Results of plugged-in tools benefit from scientific transparency and reproducibility within the research group. Furthermore, if saved configurations match while starting an evaluation plugin, the system suggests to use results already produced by other users – saving CPU/h, I/O, disk space and time. The efficient interaction between different technologies improves the Earth system modeling science.

## Guides:
Find details for users, developers, and admins of Freva in the guides.

https://github.com/FREVA-CLINT/Freva/tree/master/docu/guides

### Install:

First you will need the installation script which can be downloaded using the `wget` command:

```bash
$: wget wget -r -H -N --cut-dirs=2 --content-disposition -I "/v1/" "https://swift.dkrz.de/v1/dkrz_3d3c7abc-1681-4012-b656-3cc1058c52a9/public/install_freva-dev.sh?temp_url_sig=c2631336fdc8a288a530bc423c8433a4d3dfb1ef&temp_url_prefix=&temp_url_expires=2295-02-24T15:00:20Z"
```
Once downloaded make the script executable 

```bash
$: chmod +x install_freva-dev.sh
```

Inside the script you can adjust some settings. The most important setttings are:

- NameYourEvaluationSystem
- Path2Eva
- GitBranch

once edited the script can be executed

```bash
:$ ./install_freva-dev.sh
```
