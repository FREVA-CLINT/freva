# makefile used for testing
#
#
export PATH := $(FREVA_ENV):$(PATH):$(PWD)/src/evaluation_system/tests/mocks/bin
export MOCK_SLURM := /tmp/mock_slurm_$$RANDOM
export EVALUATION_SYSTEM_PLUGINS := $(EVALUATION_SYSTEM_PLUGINS):$(PWD)/src/evaluation_system/tests/mocks,dummy:/tmp/animator,animator
export EVALUATION_SYSTEM_CONFIG_FILE := $(PWD)/compose/local-eval-system.conf
export EVALUATION_SYSTEM_DRS_CONFIG_FILE := $(PWD)/compose/drs_config.toml
all: install test

.PHONY: docs
install:
	python3 -m pip install .[test]

test:
	python3 -m pytest -vv $(PWD)/src/evaluation_system/tests

test_coverage:
	python3 -m pytest -vv \
	    --cov=$(PWD)/src --cov-report=html:coverage_report \
	    --alluredir=test_results  --junitxml=report.xml --cov-report xml:coverage_report.xml \
		$(PWD)/src/evaluation_system/tests
	python3 -m coverage report

docs:
	make -C docs clean
	make -C docs html

prepdocs:
	rm -rf /tmp/animator
	python3 -m pip install -e .[docs]
	git clone --recursive https://gitlab.dkrz.de/freva/plugins4freva/animator.git /tmp/animator
	python3 -m ipykernel install --user --name freva
	python3 compose/dummy_user_data.py
	freva plugin animator project=observations variable=pr; echo 0





lint:
	mypy --install-types --non-interactive
	black --check -t py310 src

dummy-data:
	compose/dummy_plugin_runs.sh
	python3 compose/solr/ingest_dummy_data.py
