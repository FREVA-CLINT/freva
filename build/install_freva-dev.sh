#!/bin/bash


###############
#MAIN OPTIONS AREA
NameYourEvaluationSystem=freva-dev #project-ces WILL BE DIRECTORY in $Path2Eva
Path2Eva=$HOME/workspace/ #ROOT PATH WHERE THE PROJECTS EVALUATION SYSTEM WILL BE
# SWITCHES
makeOwnPython=True
makeFreva=True
makeConfig=True
makeStartscript=True
makeSOLRSERVER=False
makeMYSQLtables=False
GitBranch=update_tests
makeTests=True
##########
#PYTHON AREA
##########
# Install the following python packages from conda
CONDA_PKGS="cdo conda configparser 'django>=1.8,<1.9' git gitpython ipython libnetcdf mysqlclient nco netcdf4 numpy=1.9.3 pip pymysql pypdf2 pytest pytest-env pytest-cov pytest-html python-cdo"
PYTHONVERSION="3.7"
PIP_PKGS="pytest-html"
##########

###########
# MAIN CONFIG-FILE AREA
###########
ADMINS=b380001 #freva
PROJECTWEBSITE=localhost #just for info printing
USERRESULTDIR=$HOME/workspace/freva-dev/work #/home/ or /scratch or /work WHERE USERNAME HAS ALREADY A DIRECTORY e.g. /home/user
#SCHEDULER - SLURM
SLURMCOMMAND=sbatch #sbatch/None
#MYSQL
MYSQLHOST=www-regiklim.dkrz.de #localhost
MYSQLUSER=test_user #freva
MYSQLPASSWD=T3st
MYSQLDB=freva_dev #freva
#SOLR
SOLRHOST=www-regiklim.dkrz.de #localhost
SOLRUSER=b380001 #freva
SOLRPORT=8989
SOLRNAME=test_solr
#############


# END of CONFIG AREA
###############

#############
# COLLECT INFOS AND MAKE DIRS
#############
YOUREVA=$Path2Eva/$NameYourEvaluationSystem
FREVA=$YOUREVA/freva
PLUGIN=$YOUREVA/plugin4freva
DATA=$YOUREVA/data4freva
MISC=$YOUREVA/misc4freva
#Make Directories
mkdir -m 751 -p $FREVA $MISC
mkdir -m 755 -p $PLUGIN $DATA
#SUBAREA
CONFIGDIR=$MISC/config4freva
YOURPYTHON=$MISC/python4freva
STARTDIR=$MISC/loadscripts
DBDIR=$MISC/db4freva


export HDF5_DIR=$YOURPYTHON #/usr/local/hdf5
export NETCDF4_DIR=$YOURPYTHON #/usr/local/netcdf-4.3.0/gcc-4.7.2
export CDO_DIR=$YOURPYTHON #/usr/local/cdo

#Make directories
mkdir -m 777 -p $DBDIR/preview
mkdir -m 751 -p $DBDIR/solr
mkdir -m 777 -p $DBDIR/slurm
mkdir -m 751 -p $DBDIR/metadata
##############

if [ "$makeOwnPython" = "True" ]; then
    #command -v gcc >/dev/null 2>&1 || { echo >&2 "NEED gcc but it's not installed.  Aborting."; exit 1; }
    mkdir -p $YOURPYTHON
    shasum=1314b90489f154602fd794accfc90446111514a5a72fe1f71ab83e07de9504a7
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/anaconda.sh
    if [ $(sha256sum /tmp/anaconda.sh| awk '{print $1}') != $shasum ];then
        >&2 echo 'Checksums do not match'
        exit 1
    fi
    chmod +x /tmp/anaconda.sh
    /tmp/anaconda.sh -p /tmp/anaconda -b -f -u
    /tmp/anaconda/bin/conda create -c conda-forge -q -p $YOURPYTHON python=$PYTHONVERSION $CONDA_PKGS -y
    let success=$?
    rm -rf /tmp/anaconda /tmp/anaconda.sh
    [[ $success -ne 0 ]] && echo "conda create -c conda-forge -q -p $YOURPYTHON python=$PYTHONVERSION $CONDA_PKGS -y failed! EXIT" && exit 1
    if [ "$PIP_PKGS" ];then
        $YOURPYTHON/bin/python -m pip install $PIP_PKGS
        let success=$?
        [[ $success -ne 0 ]] && echo "$YOURPYTHON/bin/python -m pip install $PIP_PKGS -y failed! EXIT" && exit 1
    fi
fi

if [ "$makeFreva" = "True" ]; then
    git clone -b $GitBranch https://gitlab.dkrz.de/freva/evaluation_system.git $FREVA
fi

if [ "$makeConfig" = "True" ] ; then
    mkdir -m 751 -p $CONFIGDIR
    cat -> ${CONFIGDIR}/evaluation_system.conf <<EOF
# Freva - Freie Univ Evaluation System
# Config File
[evaluation_system]
admins=$ADMINS

project_name=$NameYourEvaluationSystem
project_website=$PROJECTWEBSITE

#: The name of the directory storing the evaluation system (output, configuration, etc)
base_dir=$NameYourEvaluationSystem

#: The location of the directory defined in $base_dir
#: We are storing this in the user home at this time since it's being used as
#:a tool-box.
base_dir_location=$USERRESULTDIR

#: work directory for the SLURM scheduler
#: when empty, the configuration will be read from User-object
scheduler_input_dir=/tmp/slurm
scheduler_output_dir=$DBDIR/slurm
scheduler_command=$SLURMCOMMAND

#: path to copy the preview to
preview_path=$DBDIR/preview

#: root path of projectdata
project_data=$DATA/crawl_my_data

#: make scratch dir browseable for website
scratch_dir=None

#: Type of directory structure that will be used to maintain state:
#:
#:    local   := <home>/<base_dir>...
#:    central := <base_dir_location>/<base_dir>/<user>/...
#:    scratch := <base_dir_location>/<user>/<base_dir>...
#:
#: (no user info in local since that is included in the home directory already)
directory_structure_type=scratch

number_of_processes = 6

#: database path


#: fuse certificates settings
#private_key=/miklip/integration/evaluation_system/database/fuse/esg_cert/credentials.pem
#cadir=/miklip/integration/evaluation_system/database/fuse/esg_cert/certificates
#esgf_host=esgf-data.dkrz.de
#esgf_port=7512
#esgf_user=None
#esgf_passw=None

#: fuse ESGF log + cache directory
#esgf_logcache=None #Should be frevadmin

#: fuse wget options
#wget_path=/usr/bin/wget
#parallel_downloads=3

#: fuse esgf nodes
#esgf_server=esgf-data.dkrz.de,pcmdi9.llnl.gov,esgf-index1.ceda.ac.uk,esgf-node.ipsl.fr,esg-dn1.nsc.liu.se

#: mySQL settings
db.host=$MYSQLHOST
db.user=$MYSQLUSER
db.passwd=$MYSQLPASSWD
db.db=$MYSQLDB


#group for external users
#external_group=frevaext

#: Define access to the solr instance
solr.host=$SOLRHOST
solr.port=$SOLRPORT
solr.core=files
solr.name=$SOLRNAME
solr.user=$SOLRUSER
solr.memory=4096M
solr.heap_size=512M
solr.root=$DBDIR/solr/
solr.server=$DBDIR/solr/server/
solr.incoming=$DBDIR/solr/incoming/
solr.processing=$DBDIR/solr/processing/
solr.backup=$DBDIR/solr/backup/

#shellinabox
#shellmachine=None
#shellport=4200

#[scheduler_options]
#module_command=$FREVA/modules/freva/1.0
#extra_modules=None
#source=None
#option_partition=None

#[scheduler_options_extern]
#module_command=$FREVA/modules/freva/1.0
#extra_modules=None
#source=None
#option_partition=None


#[plugin:movieplotter]
#python_path=$PLUGIN/movieplotter/src
#module=movieplotter


EOF
    rm -f ${FREVA}/etc/evaluation_system.conf
    ln -s ${CONFIGDIR}/evaluation_system.conf ${FREVA}/etc/evaluation_system.conf

    cat -> ${CONFIGDIR}/file.py <<EOF
"""
.. moduleauthor:: christopher kadow / Sebastian Illing
.. first version written by estanislao gonzalez

The module encapsulates all methods for accessing files on the system.
These are mainly model and observational and reanalysis data.
"""
import json
import glob
import os
import logging
from evaluation_system.misc.utils import find_similar_words
log = logging.getLogger(__name__)


CMIP5 = 'cmip5'
"""DRS structure for CMIP5 Data"""
BASELINE0 = 'baseline0'
"""DRS structure for Baseline 0 Data (it's a subset of CMIP5 data)"""
OBSERVATIONS = 'observations'
"""DRS structure for observational data."""
REANALYSIS = 'reanalysis'
"""CMOR structure for reanalysis data."""
CRAWLMYDATA = 'crawl_my_data'
"""CMOR structure for user data."""

class DRSFile(object):
    """Represents a file that follows the
    DRS <http://cmip-pcmdi.llnl.gov/cmip5/docs/cmip5_data_reference_syntax.pdf> standard."""
    # Lazy initialized in find_structure_from_path
    DRS_STRUCTURE_PATH_TYPE = None
    DRS_STRUCTURE = {
        # cmip5 data
        CMIP5: {
         "root_dir": "$DATA/model/global",
         "parts_dir": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version/variable/file_name".split('/'),
         "parts_dataset": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble//variable".split('/'),
         "parts_versioned_dataset": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version/variable".split('/'),
         "parts_file_name": "variable-cmor_table-model-experiment-ensemble-time".split('-'),
         "parts_time": "start_time-end_time",
         "data_type": CMIP5,
         "defaults": {"project": "cmip5" }
         },
        # observations
         OBSERVATIONS: {
         "root_dir": "$DATA",
         "parts_dir": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version/variable/file_name".split('/'),
         "parts_dataset": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble//variable".split('/'),
         "parts_versioned_dataset": "project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version/variable".split('/'),
         "parts_file_name": "variable-experiment-level-version-time".split('-'),
         "parts_time": "start_time-end_time",
         "data_type": OBSERVATIONS,
         "defaults": {"project": "observations"}
         },
         REANALYSIS : {
         "root_dir": "$DATA",
         "parts_dir": "project/product/institute/model/experiment/time_frequency/realm/variable/ensemble/file_name".split('/'),
         "parts_dataset": "project/product/institute/model/experiment/time_frequency/realm/variable".split('/'),
         "parts_file_name": "variable-cmor_table-project-experiment-ensemble-time".split('-'),
         "parts_time": "start_time-end_time",
         "data_type": REANALYSIS,
         "defaults": {"project": "reanalysis", "product": "reanalysis"}
        },
         CRAWLMYDATA : {
         "root_dir": "$DATA/crawl_my_data",
         "parts_dir": "project/product/institute/model/experiment/time_frequency/realm/variable/ensemble/file_name".split('/'),
         "parts_dataset": "project.product.institute.model.experiment.time_frequency.realm.variable.ensemble".split('.'),
         "parts_file_name": "variable-cmor_table-model-experiment-ensemble-time".split('-'),
         "parts_time": "start_time-end_time",
         "data_type": CRAWLMYDATA,
         "defaults": {}
         },
         # ADDMORE

             }
    """Describes the DRS structure of different types of data. The key values of this dictionary are:

root_dir
    Directory from where this files are to be found

parts_dir
    list of subdirectory category names the values they refer to (e.g. ['model', 'experiment'])

parts_dataset
    The components of a dataset name (this data should also be found in parts_dir)

parts_versioned_dataset (optional)
    If this datasets are versioned then define the version structure of them (i.e. include the version number in the dataset name)

parts_file_name
    elements composing the file name (no ".nc" though)

data_type
    same value as this key structure (for reverse traverse)

defaults
    list with values that "shouldn't" be required to be changed (e.g. for observations, project=obs4MIPS)
"""
EOF

    cat $FREVA/src/evaluation_system/model/bottom4filepy >> ${CONFIGDIR}/file.py
#    ln -s ${CONFIGDIR}/file.py $FREVA/src/evaluation_system/model/file.py
    mkdir -p $DATA/model/global/cmip5 $DATA/crawl_my_data $DATA/reanalysis $DATA/observations
fi

if [ "$makeStartscript" = "True" ] ; then
    mkdir -p $STARTDIR
    cat -> ${STARTDIR}/loadfreva.source <<EOF
#!/bin/bash -l
export PYTHONPATH=$FREVA/src
export PATH=$FREVA/bin:$YOURPYTHON/bin:$PATH
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$YOURPYTHON/lib:$NETCDF4_DIR/lib
. $FREVA/etc/autocomplete.bash
alias python=$YOURPYTHON/bin/python
freva
EOF

    cat -> ${STARTDIR}/loadfreva.modules <<EOF
#%Module1.0#####################################################################
##
## FREVA - Free Evaluation Framework modulefile
##
#
### BEGIN of config part ********
set PROJECT $NameYourEvaluationSystem
set PROJECTINFO $PROJECTWEBSITE
set PATH2FREVA $FREVA
set PATH2PYTHON $YOURPYTHON
set PATH2NETCDF $NETCDF4_DIR
set PATH2CDO $CDO_DIR

### END of config part

### BEGIN of general part ********
#define some variables
set shell [module-info shell]
set modName [module-info name]
set toolName evaluation_system
set curMode [module-info mode]
#clean symbolic links (if any)
catch { set ModulesCurrentModulefile [file readlink $ModulesCurrentModulefile] }


module-whatis   "evaluation_system v0.1"
proc ModulesHelp { } {
    puts stderr "evaluation_system 0.1"
}
### END of general part

#help function to show user help when loading module
proc show_info {}  {
    puts stderr {
$NameYourEvaluationSystem by Freva
Available commands:
  --plugin       : Applies some analysis to the given data.
  --history      : provides access to the configuration history
  --databrowser  : Find data in the system
  --crawl_my_data: Use this command to update your projectdata.
  --esgf         : Browse ESGF data and create wget script

Usage: freva --COMMAND [OPTIONS]
To get help for the individual commands use
  freva --COMMAND --help
  }
}


#only one version at a time!!
conflict evaluation_system


#pre-requisites
if { \$curMode eq "load" } {
	if { \$shell == "bash" || \$shell == "sh" } {
		        puts ". \$PATH2FREVA/etc/autocomplete.bash;"
			puts stderr "\$PROJECT Evaluation System by Freva successfully loaded."
			puts stderr "If you are using bash, try the auto complete feature for freva and freva --databrowser
by hitting tab as usual."
			puts stderr "For more help/information check: $PROJECTINFO"
			show_info
			} else {
		puts stderr "WARNING: Evaluation System is maybe NOT fully loaded, please type 'bash -l' "
		puts stderr "And load it again -> module load evaluation_system"
		puts stderr "Your shell now: \$shell"
		}
} elseif { \$curMode eq "remove" } {
	puts stderr "\$PROJECT Evaluation System successfully unloaded."
}

# SET BINARY PATHES
prepend-path PATH "\$PATH2FREVA/bin"
prepend-path PATH "\$PATH2CDO/bin"
prepend-path PATH "\$PATH2PYTHON/bin"
# SET LIBRARY PATHES
prepend-path LD_LIBRARY_PATH "\$PATH2PYTHON/lib"
prepend-path LD_LIBRARY_PATH "\$PATH2PYTHON/myfuse/lib64"
prepend-path LD_LIBRARY_PATH "\$PATH2NETCDF/lib"
# SET THE PYTHON PACKAGES the pythonpath so it can be used anywhere
append-path PYTHONPATH "\$PATH2FREVA/src"
#set python egg to stream output
setenv PYTHON_EGG_CACHE "/tmp"

# SET PYTHON ALIAS BECAUSE OF LOADING BUG
set-alias python \$PATH2PYTHON/bin/python
EOF

fi

if [ "$makeSOLRSERVER" = "True" ] ; then
    [[ ! -e "${CONFIGDIR}/evaluation_system.conf" ]] && echo "not found -> ${CONFIGDIR}/evaluation_system.conf" && exit
    [[ ! -e "${FREVA}/etc/evaluation_system.conf" ]] && echo "not found -> ${FREVA}/etc/evaluation_system.conf" && exit
    [[ ! -e "$FREVA/etc/getvar_conf.sh" ]] && echo "not found -> $FREVA/etc/getvar_conf.sh" && exit
    mkdir -m 777 -p $($FREVA/etc/getvar_conf.sh solr.incoming)
    mkdir -m 777 -p $($FREVA/etc/getvar_conf.sh solr.processing)
    mkdir -m 777 -p $($FREVA/etc/getvar_conf.sh solr.backup)
    SOLRSERVER=$($FREVA/etc/getvar_conf.sh solr.server)"/"$($FREVA/etc/getvar_conf.sh solr.name)
    SOLRHOST=$($FREVA/etc/getvar_conf.sh solr.host)
    mkdir -p $SOLRSERVER/SOLRTMP $SOLRSERVER/home $SOLRSERVER/var $SOLRSERVER/log
    wget http://archive.apache.org/dist/lucene/solr/4.2.0/solr-4.2.0.tgz -O $SOLRSERVER/solr.tgz
    tar -xvf $SOLRSERVER/solr.tgz -C $SOLRSERVER/SOLRTMP --strip-components 1 >/dev/null
    cp -r $SOLRSERVER/SOLRTMP/example/* $SOLRSERVER
    cp -r $SOLRSERVER/solr/collection1 $SOLRSERVER/home/files
    cp -r $SOLRSERVER/solr/collection1 $SOLRSERVER/home/latest
    cp -r $FREVA/etc/solr/home/files/conf/* $SOLRSERVER/home/files/conf/
    cp -r $FREVA/etc/solr/home/latest/conf/* $SOLRSERVER/home/latest/conf/
    $FREVA/sbin/solr_server start
    sleep 5
    curl "http://${SOLRHOST}:${SOLRPORT}/solr/admin/cores?action=CREATE&name=files&instanceDir=$SOLRSERVER/home/files"
    curl "http://${SOLRHOST}:${SOLRPORT}/solr/admin/cores?action=CREATE&name=latest&instanceDir=$SOLRSERVER/home/latest"
fi


if [ "$makeMYSQLtables" = "True" ] ; then
    echo "WARNING WARNING WARNING"
    echo "When no error occurs, and bash asks for the MYSQL password..."
    echo "type password 2 create mysql tables, existing tables will be OVERWRITTEN"
    echo "type ctrl -d to abort"
    mysql -u $MYSQLUSER -p $MYSQLDB -h $MYSQLHOST < $FREVA/scripts/database/create_tables_20151214.sql
fi

if [ "$makeTests" = "True" ];then

    cd $FREVA/src/evaluation_system && make test
fi
