# makefile used for testing
#
#
export PATH := $(FREVA_ENV)/bin:$(PATH):$(PWD)/src/evaluation_system/tests/mocks/bin
export MOCK_SLURM := /tmp/mock_slurm_$$RANDOM
all: test upload
test:
	rm -f .include
	pytest -vv \
	    --cov=$(PWD)/src/evaluation_system --cov-report=html:coverage_report --cov-report term-missing \
	    --html test_results/index.html  --junitxml=report.xml \
		$(PWD)/src/evaluation_system/tests
upload:
	/work/ch1187/regiklim-ces/freva/xarray/bin/swift-upload public test_results -c freva-dev
