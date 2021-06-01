#!/bin/bash
#
# Run initdb, then start services in the foreground
set -xe
sudo service mysql start
exec /opt/docker-solr/scripts/solr-foreground &
wait

