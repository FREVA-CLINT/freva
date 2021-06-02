#!/bin/bash
set -e
#source /opt/evaluation_system/bin/activate
#/opt/evaluation_system/bin/activate init --all &> /dev/null
#/opt/evaluation_system/bin/conda activate /opt/evaluation_system

/usr/bin/git config --global init.defaultBranch main &> /dev/null
/usr/bin/git config --global user.email "user@docker.org" &> /dev/null
/usr/bin/git config --global user.name "Freva" &> /dev/null

export PATH=/opt/evaluation_system/bin:$PATH
if [ -z "$(ps aux|grep mysqld_safe|grep -v grep)" ];then
    mysqld_safe &
fi

if [ -Z "$(ps aux|grep solr|grep -v grep|grep java)" ];then
    /opt/solr/bin/solr start
fi
exec /opt/docker-solr/scripts/docker-entrypoint.sh "$@"
