#!/bin/bash
set -e
/usr/bin/git config --global init.defaultBranch main &> /dev/null
/usr/bin/git config --global user.email "user@docker.org" &> /dev/null
/usr/bin/git config --global user.name "Freva" &> /dev/null
sleep 0.5
export PATH=/opt/evaluation_system/bin:$PATH
exec /opt/docker-solr/scripts/docker-entrypoint.sh "$@"
