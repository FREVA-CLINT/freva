#!/bin/bash
#
# Run initdb, then start services in the foreground
set -e
if [ "$VERBOSE" == "yes" ];then
    set -xe
fi
if [ -z "$(ps aux|grep mysqld_safe|grep -v grep)" ];then
    mysqld_safe &
    sleep 1
fi

if [ -z "$(ps aux|grep solr|grep -v grep|grep java)" ];then
    export SOLR_HOME=${HOME}/solr/data
    export SOLR_PID_DIR=${HOME}/solr
    export SOLR_LOGS_DIR=${HOME}/solr/logs
    export LOG4J_PROPS=${HOME}/solr/log4j2.xml
    exec solr-fg -s ${HOME}/solr/data  1> /dev/null &
fi
wait
