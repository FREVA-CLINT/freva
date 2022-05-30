#!/bin/bash
set -e
if [ "$VERBOSE" == "yes" ];then
    set -xe
fi
nohup mysqld_safe &> /dev/null &
solr start -s ${SOLR_HOME} -v
if [ "${IS_BINDER}" = "true" ];then
    cd ~/.evaluation_system && make dummy-data && cd ~
    rm -r ~/.evaluation_system
    cd ~
fi
exec "$@"
