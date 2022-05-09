# makefile used for testing
#
#
export PATH := $(FREVA_ENV):$(PATH):$(PWD)/src/evaluation_system/tests/mocks/bin
export MOCK_SLURM := /tmp/mock_slurm_$$RANDOM
all: install test

.PHONY: docs
install:
	python3 -m pip install .[test]

test:
	python3 -m pytest -vv $(PWD)/src/evaluation_system/tests

test_coverage:
	python3 -m pytest -vv \
	    --cov=$(PWD)/src --cov-report=html:coverage_report --cov-report term-missing \
	    --alluredir=test_results  --junitxml=report.xml \
		$(PWD)/src/evaluation_system/tests

docs:
	export EVALUATION_SYSTEM_CONFIG_FILE := $(PWD)/compose/local-eval-system.conf
	export EVALUATION_SYSTEM_DRS_CONFIG_FILE := $(PWD)/compose/drs_config.toml
	export EVALUATION_SYSTEM_PLUGINS := $(EVALUATION_SYSTEM_PLUGINS):$(PWD)/src/evaluation_system/tests/mocks,dummy
	make -C docs clean
	make -C docs html

prepdocs:
	export EVALUATION_SYSTEM_CONFIG_FILE := $(PWD)/compose/local-eval-system.conf
	export EVALUATION_SYSTEM_DRS_CONFIG_FILE := $(PWD)/compose/drs_config.toml
	export EVALUATION_SYSTEM_PLUGINS := $(EVALUATION_SYSTEM_PLUGINS):$(PWD)/src/evaluation_system/tests/mocks,dummy
	rm -rf /tmp/animator
	python3 -m pip install -e .[docs]
	git clone --recursive https://gitlab.dkrz.de/freva/plugins4freva/animator.git /tmp/animator
	python3 -m ipykernel install --user --name freva
	make dummy-data
	freva plugin animator project=observations variable=pr; echo 0





lint:
	mypy
	black --check -t py39 src

dummy-data:
	compose/dummy_plugin_runs.sh
	python3 compose/solr/ingest_dummy_data.py
