# makefile used for testing
#
#
SHELL := /bin/bash
$(shell cat ../../../misc4freva/loadscripts/loadfreva.source|grep -v autocomplete|grep -v ^freva > .include)
include .include
export $(shell sed 's/=.*//' .include)
test:
	rm -f .include
	python3 -m coverage run --source=$(PWD) -m pytest -vv $(PWD)/tests
	python3 -m coverage html -d codecov --omit='external/*,fuse/*'
	python3 -m coverage report --omit='external/*,fuse/*' -m
