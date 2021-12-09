set -e
# `crawl` MUST be fully qualified but nothing else needs to be (including the `root_dir` in the DRS config)
sbin/solr_ingest --debug --crawl=$PWD/.docker/data --output=.docker/solr_digest --solr-url=localhost:8983
sbin/solr_ingest --debug --ingest=.docker/solr_digest --solr-url=localhost:8983