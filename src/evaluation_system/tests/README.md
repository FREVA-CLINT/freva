Run the tests with coverage:
--

1. Load virtual python
. vepy/bin/activate

2. Start solr server
cd tests/solr_server/test_solr
java -server -Xmx100M  -Dsolr.solhome=/home/illing/workspace/evaluation_system/src/evaluation_system/tests/solr_server/test_solr/solr -jar start.jar

3. Run the tests
cd src/evaluation_system
nosetests -s -x --with-coverage  --cover-package=. --cover-tests --cover-html --cover-erase --cover-inclusive tests/



