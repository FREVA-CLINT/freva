TEST_EVAL = """[evaluation_system]
base_dir=evaluation_system
project_name=freva-ces
base_dir_location=/tmp/evaluation_system_test
scratch_dir=/tmp/scratch/$$USER
directory_structure_type=central
scheduler_input_dir=/tmp/slurm
scheduler_output_dir=/tmp/slurm
scheduler_system=slurm
preview_path=/tmp/preview
project_data=/tmp/user_data
db.host=127.0.0.1
db.user=freva
db.passwd=T3st
db.db=freva
solr.host=localhost
solr.port=8983
solr.core=files
[scheduler_options]
source=$$EVALUATION_SYSTEM_HOME/activate_sh
queue=compute
project=ch1187
memory=10G
[plugin:DummyPlugin]
plugin_path=$$EVALUATION_SYSTEM_HOME/src/evaluation_system/tests/mocks
python_path=$$EVALUATION_SYSTEM_HOME/src/evaluation_system/tests/mocks
module=dummy"""

TEST_DRS = """
[cmip5]
root_dir = "/mnt/data4freva/model/global"
parts_dir = [ "project", "product", "institute", "model", "experiment", "time_frequency",
    "realm", "cmor_table", "ensemble", "version", "variable",
]
parts_file_name = [ "variable", "cmor_table", "model", "experiment", "ensemble", "time", ]
parts_time = "start_time-end_time"

[cmip5.defaults]
project = "cmip5"

[observations]
root_dir = ".docker/data"
parts_dir = [
    "project", "product", "institute", "model", "experiment", "time_frequency",
    "realm", "cmor_table", "ensemble", "version", "variable",
]
parts_versioned_dataset = [
    "project", "product", "institute", "model", "experiment", "time_frequency",
    "realm", "cmor_table", "ensemble", "version", "variable",
]
parts_file_name = ["variable", "experiment", "level", "version", "time"]
parts_time = "start_time-end_time"

[observations.defaults]
project = "observations"

[reanalysis]
root_dir = "/mnt/data4freva"
parts_dir = [
    "institute", "model", "experiment", "time_frequency",
    "realm", "ensemble", "variable",
]
parts_file_name = [
    "variable", "cmor_table", "project", "experiment", "ensemble", "time",
]
parts_time = "start_time-end_time"

[reanalysis.defaults]
project = "reanalysis"
product = "reanalysis"

[crawl_my_data]
root_dir = "/tmp/user_data"
parts_dir = [
    "project", "product", "institute", "model", "experiment", "time_frequency",
    "realm", "cmor_table", "ensemble", "version", "variable"
]
parts_file_name = [
    "variable", "cmor_table", "model", "experiment", "ensemble", "time",
]
parts_time = "start_time-end_time"
"""
