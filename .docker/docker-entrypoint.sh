#!/bin/bash
set -e
if [ "$VERBOSE" == "yes" ];then
    set -xe
fi
source /usr/local/bin/docker-entrypoint.sh
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
mariadbd --user=${MARIADB_USER} --datadir=${MYSQL_DATA_DIR} --socket=/run/mysqld/mysqld.sock --console &
until mariadb-admin ping --user="${MARIADB_USER}" --password="${MARIADB_PASSWORD}" --socket="/run/mysqld/mysqld.sock" --silent;
do
    echo "waiting for mariadb"
    sleep 1
done

solr start -s ${SOLR_HOME}
if [ "${IS_BINDER}" = "true" ];then
    python $EVAL_HOME/ingest_dummy_data.py /mnt/data4freva
    python $EVAL_HOME/dummy_user_data.py
    for i in 1 2 3 4 5; do
        freva plugin dummyplugin the_number=$i
    done
fi
exec "$@"
