################################
Welcome to the Freva BETA
Free Evaluation System Framework for Earth System Modeling
################################

INFO:
This is the BETA version of the Freva framwork. Goto freva.met.fu-berlin.de, click on 'Guest?', login, and browse the evaluation system at the Freie Universität Berlin (GERMANY).

What is Freva?
Freva is an all-in-one solution to efficiently handle evaluation and validation systems of research projects, institutes or universities in the Earth system and climate modeling community. It is a hybrid scientific software framework for high performance computing, including all features present in the shell and web environment. The main system design features the common and standardized model database, programming interface, and history of evaluations. The database interface satisfies the international data standards provided by the Earth System Grid Federation and the World Climate Research Programme. Freva indexes different data projects into one common search environment by storing the meta data information of the model, reanalysis and observational data sets in a database. This implemented meta data system with its advanced but easy-to-handle search tool supports at different stages: users, developers and their plugins to retrieve the required information of the database. A generic application programming interface allows scientific developers to connect their analysis tools with the evaluation system independently of the programming language used. Users of the evaluation techniques benefit from the common interface of the evaluation system without any need to understand the different scripting languages. The history and configuration sub-system stores every analysis performed with the evaluation system in a database. Configurations and results of the tools can be shared among scientists via shell or web system. Results of plugged-in tools benefit from scientific transparency and reproducibility within the research group. Furthermore, if saved configurations match while starting an evaluation plugin, the system suggests to use results already produced by other users – saving CPU/h, I/O, disk space and time. The efficient interaction between different technologies improves the Earth system modeling science.

Guides:
Find details for users, developers, and admins of Freva in the guides.

https://github.com/FREVA-CLINT/Freva/tree/master/docu/guides

Install:

Detailed installation information you find in the BAG - Basic Admin Guide
https://github.com/FREVA-CLINT/Freva/blob/master/docu/guides/bag.pdf
(TO BE UPDATED)

Quick Install:

Quick Installation Guide - the fastest way, if you knowwhat yoo do

##############
Step 1: Needed Software
MySQL server: Install, give access to it, and open its port.
SOLR port: Open port 8983.
SLURM scheduler: Install it.
Software: bash, mysql, git, python-dev, java (1.6, 1.7, 1.8), libmysql(-dev), libffi(-dev),
libssl(-dev), libsabl(-dev), httpd(-dev), netcdf4, hdf5, cdo, nco, wget, curl

##############
Step 2: The Install-Script
Download install-script:
wget https://github.com/FREVA-CLINT/Freva/blob/master/build/install.sh
Adapt install-script: Fill out the config area and execute it with switched switches

#############
Step 3: The Basic Setup and Testing
Load Freva: modules or source
ls /path/2/project−ces/misc4freva/loadscripts/
Test plugin:
export EVALUATION SYSTEM PLUGINS=/path/2/project−ces/plugins4freva,example;
freva −−plugin ExamplePlugin project=bla product=bla institute=bla model=bla
Test history:
freva −−history ENTER
Test databrowser:
ln −s /path/2/project−ces/misc4freva/db4freva/cmor4freva/examplestructure4solr/project /path/2/project−ces/data4freva/crawl_my_data/project
/path/2/project−ces/freva/sbin/solr_server path2ingest /path/2/project−ces/data 4freva/crawl_ my_ data/project
freva −−databrowser ENTER
Test crawl my data:
mkdir /path/2/project-ces/data4freva/crawl_my_data/user-smith
ln -s /path/2/project-ces/misc4freva/db4freva/cmor4freva/example_structure4solr/project/product /path/2/project-ces/data4freva/crawl_my_data/user-smith/product
freva --crawl_my_data 
freva --databrowser project=user-smith ENTER
Test batchmode:
freva --plugin ExamplePlugin project=user-smith product=product institute=institute model=model experiment=experiment time_frequency=time_frequency variable=variable --batchmode=True

