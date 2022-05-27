#!/bin/bash
set -e
if [ "$VERBOSE" == "yes" ];then
    set -xe
fi
/usr/bin/git config --global init.defaultBranch main &> /dev/null
/usr/bin/git config --global user.email "user@docker.org" &> /dev/null
/usr/bin/git config --global user.name "Freva" &> /dev/null
export PATH=/opt/evaluation_system/bin:$PATH
mysqld_safe &> ${MYSQL_LOGS_DIR}/mysqld-3306-console.log &
/opt/solr/bin/solr start -s ${SOLR_HOME} -v
exec "$@"
