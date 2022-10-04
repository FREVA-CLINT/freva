#!/bin/bash
set -e
if [ "$VERBOSE" == "yes" ];then
    set -xe
fi
mariadbd  &
/usr/local/bin/docker-entrypoint.sh
solr start -s ${SOLR_HOME}
if [ "${IS_BINDER}" = "true" ];then
    python $EVAL_HOME/ingest_dummy_data.py /mnt/data4freva
    python $EVAL_HOME/dummy_user_data.py
    for i in 1 2 3 4 5; do
        freva plugin dummyplugin the_number=$i
    done
fi
exec "$@"
