from evaluation_system.api.workload_manager.sge import SGEJob


def test_job_script(tmpdir):
    log_directory = tmpdir.strpath
    with SGEJob(
        cores=6,
        processes=2,
        memory="12GB",
        queue="my-queue",
        project="my-project",
        walltime="02:00:00",
        env_extra=["export MY_VAR=my_var"],
        job_extra=["-w e", "-m e"],
        log_directory=log_directory,
        resource_spec="h_vmem=12G,mem_req=12G",
    ) as cluster:
        job_script = cluster.job_script()

        for each in [
            "-q my-queue",
            "-P my-project",
            "-l h_rt=02:00:00",
            "export MY_VAR=my_var",
            "#$ -w e",
            "#$ -m e",
            "#$ -e {}".format(log_directory),
            "#$ -o {}".format(log_directory),
            "-l h_vmem=12G,mem_req=12G",
            "#$ -cwd",
            "#$ -j y",
        ]:
            assert each in job_script
