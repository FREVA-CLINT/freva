#!/bin/bash
set -e
#source /opt/evaluation_system/bin/activate
#/opt/evaluation_system/bin/activate init --all &> /dev/null
#/opt/evaluation_system/bin/conda activate /opt/evaluation_system
exec /opt/docker-solr/scripts/docker-entrypoint.sh "$@"
