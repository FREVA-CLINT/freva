#!/bin/bash
set -e
if [ "$VERBOSE" == "yes" ];then
    set -xe
fi
source /usr/local/bin/docker-entrypoint.sh
set -- mariadbd
# call main bits of the mariadb entrypoint to have DB initialized
docker_setup_env "$@"
docker_create_db_directories "$@"
# there's no database, so it needs to be initialized
if [ -z "$DATABASE_ALREADY_EXISTS" ]; then
    docker_verify_minimum_env "$@"
    docker_mariadb_init "$@"
elif _check_if_upgrade_is_needed; then
    docker_mariadb_upgrade "$@"
fi
mariadbd --user=${MARIADB_USER} --datadir=${MYSQL_DATA_DIR} --socket=/tmp/mysql.sock --console &
until mariadb-admin ping --user="${MARIADB_USER}" --password="${MARIADB_PASSWORD}" --socket="/tmp/mysql.sock" --silent;
do
    echo "waiting for mariadb"
    echo "${MARIADB_USER} ${MARIADB_PASSWORD}"
    sleep 1
done

solr start -s ${SOLR_HOME}
if [ "${IS_BINDER}" = "true" ];then
    # wait for solr to be up
    solr_status_url="http://localhost:8983/solr/admin/cores?action=STATUS"
    until curl -s "$solr_status_url" > /dev/null; do
        echo "Waiting for Solr to be available..."
        sleep 2
    done
    echo "Solr is up!"
    python $EVAL_HOME/ingest_dummy_data.py /mnt/data4frev
    python $EVAL_HOME/dummy_user_data.py
    for i in 1 2 3 4 5; do
        freva plugin dummyplugin the_number=$i
    done
fi
exec "$@"
