#!/bin/bash
set -e
if [ "$VERBOSE" == "yes" ];then
    set -xe
fi
export PATH=/opt/evaluation_system/bin:$PATH
mysqld_safe &> ${MYSQL_LOGS_DIR}/mysqld-3306-console.log &
/opt/solr/bin/solr start -s ${SOLR_HOME} -v
if [ "${IS_BINDER}" = "true" ];then
    cd ~/.evaluation_system && make dummy-data && cd ~
    rm -r ~/.evaluation_system
fi
exec "$@"
