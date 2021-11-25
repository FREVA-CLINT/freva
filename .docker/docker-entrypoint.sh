#!/bin/bash
set -e
/usr/bin/git config --global init.defaultBranch main &> /dev/null
/usr/bin/git config --global user.email "user@docker.org" &> /dev/null
/usr/bin/git config --global user.name "Freva" &> /dev/null
sleep 0.5
export PATH=/opt/evaluation_system/bin:$PATH

nohup mysqld_safe &
export SOLR_HOME=${HOME}/solr/data
export SOLR_PID_DIR=${HOME}/solr
export SOLR_LOGS_DIR=${HOME}/solr/logs
export LOG4J_PROPS=${HOME}/solr/log4j2.xml
sleep 0.5
/opt/solr/bin/solr start 1> /dev/null
exec /opt/docker-solr/scripts/docker-entrypoint.sh "$@"
