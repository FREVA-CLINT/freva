# makefile used for testing
#
#
export PATH := $(FREVA_ENV)/bin:$(PATH)
all: test upload
test:
	rm -f .include
	pytest -vv \
	    --cov=$(PWD)/src/evaluation_system --cov-report=html:public --cov-report term-missing \
	    --html test_results/index.html \
		$(PWD)/src/evaluation_system/tests
upload:
	/work/ch1187/regiklim-ces/freva/xarray/bin/swift-upload public test_results -c freva-dev
