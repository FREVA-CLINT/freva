TEST_EVAL = """[evaluation_system]
base_dir=evaluation_system
project_name=freva-ces
base_dir_location=/tmp/evaluation_system_test
scratch_dir=/tmp/scratch/$$USER
directory_structure_type=central
scheduler_input_dir=/tmp/slurm
scheduler_output_dir=/tmp/slurm
scheduler_command=sbatch
scheduler_options='--begin now'
preview_path=/tmp/preview
project_data=/tmp/crawl_my_data
db.host=127.0.0.1
db.user=freva
db.passwd=T3st
db.db=freva
solr.host=localhost
solr.port=8983
solr.core=files
[scheduler_options]
module_command=$$EVALUATION_SYSTEM_HOME/loadfreva.modules
option_partition=compute
option_account=ch1187
option_mem=0
[plugin:DummyPlugin]
plugin_path=$$EVALUATION_SYSTEM_HOME/src/evaluation_system/tests/mocks
python_path=$$EVALUATION_SYSTEM_HOME/src/evaluation_system/tests/mocks
module=dummy"""
