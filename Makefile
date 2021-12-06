# makefile used for testing
#
#
export PATH := $(FREVA_ENV):$(PATH):$(PWD)/src/evaluation_system/tests/mocks/bin
export MOCK_SLURM := /tmp/mock_slurm_$$RANDOM
all: install test

bla:
	echo $(PATH)
install:
	python3 -m pip install .[test]
test:
	pytest -vv \
	    --cov=$(PWD)/src --cov-report=html:coverage_report --cov-report term-missing \
	    --alluredir=test_results  --junitxml=report.xml \
		$(PWD)/src/evaluation_system/tests
