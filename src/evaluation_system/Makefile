# makefile used for testing
#
#
test:
	. ../../../misc4freva/loadscripts/loadfreva.source
	python3 -m coverage run --source=$(PWD) -m pytest -vv $(PWD)/tests
	python3 -m coverage report --omit='external/*,fuse/*' -m
