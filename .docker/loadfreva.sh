#!/bin/bash
#
# Run initdb, then start services in the foreground
set -e
if [ "$VERBOSE" == "yes" ];then
    set -xe
fi
if [ -z "$(ps aux|grep mysqld_safe|grep -v grep)" ];then
    mysqld_safe &
fi

if [ -z "$(ps aux|grep solr|grep -v grep|grep java)" ];then
    export SOLR_HOME=${HOME}/solr/data
    export SOLR_PID_DIR=${HOME}/solr
    export SOLR_LOGS_DIR=${HOME}/solr/logs
    export LOG4J_PROPS=${HOME}/solr/log4j2.xml
    exec solr-fg -s ${HOME}/solr/data &
fi
if [ -f /opt/evaluation_system/sbin/solr_ingest ];then
   /opt/evaluation_system/sbin/solr_ingest --crawl /mnt/data4freva/observations --output /tmp/dump.gz
   /opt/evaluation_system/sbin/solr_ingest --ingest /tmp/dump.gz;
   rm /tmp/dump.gz
fi

wait

