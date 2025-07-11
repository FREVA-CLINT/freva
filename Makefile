# makefile used for testing
#
#
export PATH := $(FREVA_ENV):$(PATH):$(PWD)/src/evaluation_system/tests/mocks/bin
export MOCK_SLURM := /tmp/mock_slurm_$$RANDOM
export EVALUATION_SYSTEM_PLUGINS := $(EVALUATION_SYSTEM_PLUGINS):$(PWD)/src/evaluation_system/tests/mocks,dummy:$(PWD)/src/evaluation_system/tests/mocks,dummyfolder:/tmp/animator,animator
export EVALUATION_SYSTEM_CONFIG_FILE := $(PWD)/compose/local-eval-system.conf
export EVALUATION_SYSTEM_DRS_CONFIG_FILE := $(PWD)/compose/drs_config.toml
PYTHON3 := $(shell which python3)
all: install test_coverage

.PHONY: docs
install:
	python3 -m pip install .[test]

test:
	python3 -m pytest -vv --nbval --current-env $(PWD)/src/evaluation_system/tests \
		--ignore=src/evaluation_system/tests/esgf_test.py

test_coverage:
	python3 -m pytest -vv \
		--nbval --current-env --cov=$(PWD)/src --cov-report=html:coverage_report \
	    --junitxml report.xml --current-env --cov-report xml \
		--ignore=src/evaluation_system/tests/esgf_test.py \
		$(PWD)/src/evaluation_system/tests
	python3 -m coverage report

prepdocs:
	rm -rf /tmp/animator
	python3 -m pip install -e .[docs]
	git clone --recursive https://gitlab.dkrz.de/freva/plugins4freva/animator.git /tmp/animator
	mkdir -p /tmp/animator/plugin_env/bin
	ln -s $(PYTHON3) /tmp/animator/plugin_env/bin/python
	python3 -m ipykernel install --user --name freva \
		--env EVALUATION_SYSTEM_CONFIG_FILE $(EVALUATION_SYSTEM_CONFIG_FILE) \
		--env EVALUATION_SYSTEM_PLUGINS $(EVALUATION_SYSTEM_PLUGINS)
	python3 -m bash_kernel.install
	rm -rf docs/source/APIRef.rst
	curl -Ls -o docs/source/api/APIRef.rst https://raw.githubusercontent.com/freva-org/freva-nextgen/main/docs/source/databrowser/APIRef.rst
	make dummy-data
	compose/animator_plugin_run.sh

docs:
	make -C docs clean
	make -C docs html

dummy-data:
	compose/dummy_plugin_runs.sh
	python3 compose/dummy_user_data.py
	python3 compose/solr/ingest_dummy_data.py

lint:
	mypy --install-types --non-interactive
	black --check -t py311 src
