#!/bin/bash
set -e
if [ "$VERBOSE" == "yes" ];then
    set -xe
fi
mysqld_safe_user &
solr start -s ${SOLR_HOME} -v
if [ "${IS_BINDER}" = "true" ];then
    cd ~/.evaluation_system && make dummy-data && cd ~
    rm -r ~/.evaluation_system
fi
exec "$@"
