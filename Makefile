# makefile used for testing
#
#
SHELL := /bin/bash
$(shell cat ../misc4freva/loadscripts/loadfreva.source|grep -v autocomplete|grep -v ^freva > .include)
include .include
export $(shell sed 's/=.*//' .include)
test:
	rm -f .include
	python3 -m pytest -vv \
	    --cov=$(PWD)/src/evaluation_system --cov-report=html:public --cov-report term-missing \
	    --html test_results/index.html \
		$(PWD)/src/evaluation_system/tests
