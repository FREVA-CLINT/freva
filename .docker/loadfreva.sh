#!/bin/bash
exec tail -f ${SOLR_LOGS_DIR}/solr-${SOLR_UID}-console.log
