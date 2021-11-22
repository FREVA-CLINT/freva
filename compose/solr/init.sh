#!/bin/bash

precreate-core latest
precreate-core files

cp /tmp/managed-schema /var/solr/data/latest/conf/managed-schema
cp /tmp/managed-schema /var/solr/data/files/conf/managed-schema
