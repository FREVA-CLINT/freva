# makefile used for testing
#
#
export PATH := $(FREVA_ENV)/bin:$(PATH):$(PWD)/src/evaluation_system/tests/mocks/bin
export MOCK_SLURM := /tmp/mock_slurm_$$RANDOM
all: test
test:
	pytest -vv \
	    --cov=$(PWD)/src/evaluation_system --cov-report=html:coverage_report --cov-report term-missing \
	    --html test_results/index.html  --junitxml=report.xml \
		$(PWD)/src/evaluation_system/tests
