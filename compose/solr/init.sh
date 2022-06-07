#!/bin/bash

precreate-core latest
precreate-core files

cp /tmp/managed-schema.xml /var/solr/data/latest/conf/managed-schema.xml
cp /tmp/managed-schema.xml /var/solr/data/files/conf/managed-schema.xml
