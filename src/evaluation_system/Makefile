# makefile used for testing
#
#
SHELL := /bin/bash
$(shell cat ../../../misc4freva/loadscripts/loadfreva.source|grep -v autocomplete|grep -v ^freva > .include)
include .include
export $(shell sed 's/=.*//' .include)
test:
	python3 -m coverage run --source=$(PWD) -m pytest -vv $(PWD)/tests
	python3 -m coverage report --omit='external/*,fuse/*' -m
	rm -f .include
