#!/bin/bash
#
# Run initdb, then start services in the foreground
set -e
if [ "$VERBOSE" == "yes" ];then
    set -xe
fi

/usr/bin/git config --global init.defaultBranch main > /dev/null
/usr/bin/git config --global user.email "user@docker.org" > /dev/null
/usr/bin/git config --global user.name "Freva" > /dev/null

mysqld_safe &
exec /opt/docker-solr/scripts/solr-foreground &
wait

