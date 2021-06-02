#!/bin/bash
#
# Run initdb, then start services in the foreground
set -e
if [ "$VERBOSE" == "yes" ];then
    set -xe
fi

exec sudo service mysql start
exec /opt/docker-solr/scripts/solr-foreground &
wait

