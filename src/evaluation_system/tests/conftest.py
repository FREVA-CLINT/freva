from collections import namedtuple
from configparser import ConfigParser, ExtendedInterpolation
import datetime
from getpass import getuser
import os
from pathlib import Path
import shutil
import socket
from tempfile import TemporaryDirectory, NamedTemporaryFile
import time

import django
from django.conf import settings
import pytest
import toml
import mock


class mock_datetime:
    def __init__(self, year, month, day):

        self._year = year
        self._month = month
        self._day = day

    def today(self):
        return datetime.datetime(self._year, self._month, self._day)


def get_config(admin=False):
    from .mocks import TEST_EVAL, TEST_DRS

    test_cfg = ConfigParser(interpolation=ExtendedInterpolation())
    test_cfg.read_string(TEST_EVAL)
    drs_cfg = toml.loads(TEST_DRS)
    cfg_p = ConfigParser(interpolation=ExtendedInterpolation())
    if admin:
        test_cfg["evaluation_system"].setdefault("admins", getuser())
    items_to_overwrite = [
        "db.host",
        "db.user",
        "db.passwd",
        "db.db",
        "db.port",
        "solr.host",
        "solr.port",
        "solr.core",
    ]
    cfg_p.read(os.environ["EVALUATION_SYSTEM_CONFIG_FILE"])
    cfg = dict(cfg_p["evaluation_system"].items())
    for key in items_to_overwrite:
        value = test_cfg["evaluation_system"].get(key)
        test_cfg.set("evaluation_system", key, cfg.get(key, value))
    return test_cfg, drs_cfg


def mock_config(keyfile, admin=False, patch_env=True):
    cfg, drs_config = get_config(admin)
    from evaluation_system.misc import config

    with TemporaryDirectory() as temp_dir:
        eval_config = Path(temp_dir) / "evaluation_system.conf"
        drs_conf_path = Path(temp_dir) / "drs_config.toml"
        crawl_data_dir = Path(temp_dir) / "data" / "user_my_data"
        drs_config["crawl_my_data"]["root_dir"] = str(crawl_data_dir)
        PATH = (Path(__file__).parent / "mocks" / "bin").absolute()
        env = dict(
            EVALUATION_SYSTEM_CONFIG_FILE=str(eval_config),
            EVALUATION_SYSTEM_DRS_CONFIG_FILE=str(drs_conf_path),
            PUBKEY=str(keyfile),
            PATH=str(PATH) + ":" + os.environ["PATH"],
        )
        with open(eval_config, "w") as f:
            cfg.write(f)
        with open(drs_conf_path, "w") as f:
            toml.dump(drs_config, f)
        if not patch_env:
            yield env
        else:
            with mock.patch.dict(os.environ, env, clear=True):
                yield config
    try:
        shutil.rmtree(config.get("base_dir_location"))
    except:
        pass


@pytest.fixture(scope="session")
def time_mock():
    with mock.patch("datetime.date", mock_datetime(1999, 9, 9)) as date_mock:
        import evaluation_system

        try:
            evaluation_system.api.user_data.date = date_mock
        except AttributeError:
            pass
        yield date_mock


@pytest.fixture(scope="function")
def temp_script():

    with NamedTemporaryFile(suffix="test.sh") as tf:
        yield tf.name


@pytest.fixture(scope="session")
def dummy_key(time_mock):
    with NamedTemporaryFile(suffix=".crt") as tf:
        with Path(tf.name).open("w") as f:
            f.write("------ PUBLIC KEY ----\n12345\n---- END PUBLIC KEY ----")
        yield tf.name


@pytest.fixture(scope="module")
def plugin_doc():

    with TemporaryDirectory() as td:
        dummy_doc = Path(td) / "dummy_plugin_doc.tex"
        dummy_bib = Path(td) / "dummy_plugin.bib"
        with (dummy_doc).open("w") as f:
            f.write(
                """\\documentclass[12pt]{article}
\\usepackage[utf8]{inputenc}
\\begin{document}
This is a dummy doc
\\end{document}"""
            )
        with (dummy_doc).open("w") as f:
            f.write(
                """% This file was created with JabRef 2.9.2.
% Encoding: UTF-8"""
            )
        yield dummy_doc


@pytest.fixture(scope="session")
def admin_env(time_mock, dummy_key):
    yield from mock_config(dummy_key, admin=True, patch_env=False)


@pytest.fixture(scope="session")
def dummy_env(time_mock, dummy_key):
    yield from mock_config(dummy_key, admin=False)


@pytest.fixture(scope="session")
def git_config():
    yield "git config init.defaultBranch main; git config user.name your_user; git; config user.email your@email.com"


@pytest.fixture(scope="module")
def dummy_git_path():
    with TemporaryDirectory(prefix="git") as td:
        repo_path = Path(td) / "test_plugin.git"
        tool_path = Path(td) / "test_tool"
        tool_path.mkdir(exist_ok=True, parents=True)
        repo_path.mkdir(exist_ok=True, parents=True)
        yield repo_path, tool_path


@pytest.fixture(scope="module")
def temp_dir():
    with TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture(scope="function")
def dummy_crawl(dummy_solr, dummy_settings, dummy_env):

    # At this point files have been ingested into the server already,
    # delete them again
    [getattr(dummy_solr, key).delete("*") for key in ("all_files", "latest")]
    from evaluation_system.misc import config

    root_path = Path(config.get_drs_config()["crawl_my_data"]["root_dir"])
    crawl_dir = root_path / f"user-{getuser()}"
    user_files = []
    for file in map(Path, dummy_solr.files):
        parts = ("foo",) + file.parts[2:]
        crawl_file = crawl_dir.joinpath(*parts)
        crawl_file.parent.mkdir(exist_ok=True, parents=True)
        crawl_file.touch()
        user_files.append(crawl_file)
    yield user_files
    [getattr(dummy_solr, key).delete("*") for key in ("all_files", "latest")]
    shutil.rmtree(root_path)


@pytest.fixture(scope="module")
def dummy_reana(dummy_solr, dummy_settings):

    from evaluation_system.model.solr_core import SolrCore

    with TemporaryDirectory(prefix="solr") as td:
        tmp_files = [
            "ECMWF/IFS/ERA-Int/3h/atmos/tas/r2i1p1/tas_3h_reana_era-int_r2i1p1_190912-193411.nc",
            "ECMWF/IFS/ERA5/hr/atmos/pr/r1ip1/pr_hr_reana_era5_r1i1p1_200811-201812.nc",
            "ECMWF/IFS/ERA5/hr/atmos/pr/r7i2p1/pr_hr_reana_era5_r7i2p1_200911-201912.nc",
            "ECMWF/IFS/ERA5/hr/atmos/pr/r7i2p1/pr_hr_reana_era5_r7i2p1_202001-202201.nc",
        ]
        files = []
        for f in tmp_files:
            abs_path = Path(dummy_solr.reana) / f
            abs_path.parent.mkdir(exist_ok=True, parents=True)
            abs_path.touch()
            files.append(str(abs_path))
        SolrCore.load_fs(
            Path(dummy_solr.reana),
            abort_on_errors=True,
            core_all_files=dummy_solr.all_files,
            core_latest=dummy_solr.latest,
        )
        yield files


@pytest.fixture(scope="module")
def dummy_solr(dummy_env, dummy_settings):

    dummy_settings.reloadConfiguration()
    server = namedtuple(
        "solr",
        [
            "solr_port",
            "solr_host",
            "all_files",
            "latest",
            "tmpdir",
            "drsfile",
            "files",
            "cmd",
            "reana",
            "DRSFILE",
        ],
    )
    server.solr_port = dummy_settings.get("solr.port")
    server.solr_host = dummy_settings.get("solr.host")
    from evaluation_system.model.solr_core import SolrCore
    from evaluation_system.model.solr import SolrFindFiles
    from evaluation_system.model.file import DRSFile
    from evaluation_system.misc.utils import supermakedirs

    server.all_files = SolrCore(
        core="files", host=server.solr_host, port=server.solr_port
    )
    server.latest = SolrCore(
        core="latest", host=server.solr_host, port=server.solr_port
    )
    server.all_files.delete("*")
    server.latest.delete("*")
    with TemporaryDirectory(prefix="solr") as td:

        supermakedirs(str(Path(td) / "solr_core"), 0o0777)
        server.tmpdir = str(
            Path(td) / "solr_core",
        )
        reana_dir = str(Path(td) / "reanalysis")
        supermakedirs(reana_dir, 0o0777)
        server.reana = reana_dir
        DRSFile._load_structure_definitions()
        orig_dir = DRSFile.DRS_STRUCTURE["cmip5"].root_dir
        old_reana = DRSFile.DRS_STRUCTURE["reanalysis"].root_dir
        DRSFile.DRS_STRUCTURE["cmip5"].root_dir = server.tmpdir
        DRSFile.DRS_STRUCTURE["reanalysis"].root_dir = reana_dir
        DRSFile.DRS_STRUCTURE_PATH_TYPE[server.tmpdir] = "cmip5"
        DRSFile.DRS_STRUCTURE_PATH_TYPE[server.reana] = "reanalysis"
        server.files = [
            "cmip5/output1/MOHC/HadCM3/historical/mon/aerosol/aero/r2i1p1/v20110728/wetso2/wetso2_aero_HadCM3_historical_r2i1p1_190912-193411.nc",
            "cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc",
            "cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110719/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc",
            "cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc",
            "cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110419/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc",
        ]
        for f in server.files:
            abs_path = Path(server.tmpdir) / f
            abs_path.parent.mkdir(exist_ok=True, parents=True)
            with abs_path.open("w") as f_out:
                f_out.write(" ")
        data_dir = Path(server.tmpdir) / "cmip5"
        # add the files to solr
        SolrCore.load_fs(
            data_dir,
            abort_on_errors=True,
            core_all_files=server.all_files,
            core_latest=server.latest,
        )
        server.DRSFile = DRSFile
        server.fn = str(Path(server.tmpdir) / server.files[0])
        server.drs = server.DRSFile.from_path(server.fn)
        yield server
    server.all_files.delete("*")
    server.latest.delete("*")
    DRSFile.DRS_STRUCTURE["cmip5"].root_dir = orig_dir
    DRSFile.DRS_STRUCTURE["reanalysis"].root_dir = old_reana


@pytest.fixture(scope="module")
def django_user(dummy_settings, dummy_env):

    from django.contrib.auth.models import User
    from evaluation_system.model.history.models import History
    from django.contrib.auth.models import User

    user_django, created = User.objects.get_or_create(username=getuser())
    yield user_django
    User.objects.filter(username=getuser()).delete()
    History.objects.all().delete()


@pytest.fixture(scope="module")
def dummy_config(dummy_env, dummy_settings_single):

    from evaluation_system.misc import config, utils

    config.reloadConfiguration()
    yield config
    config.reloadConfiguration()


@pytest.fixture(scope="module")
def dummy_plugin(dummy_env, dummy_settings):

    from evaluation_system.tests.mocks.dummy import DummyPlugin

    yield DummyPlugin()


@pytest.fixture(scope="function")
def dummy_history(dummy_env, dummy_settings):

    from evaluation_system.model.history.models import History

    yield History
    History.objects.all().delete()


@pytest.fixture(scope="module")
def test_user(dummy_env, dummy_settings, config_dict):

    from evaluation_system.model.history.models import History
    from django.contrib.auth.models import User

    user = User.objects.create_user(username="test_user2", password="123")
    hist = History.objects.create(
        timestamp=datetime.datetime.now(),
        status=History.processStatus.running,
        uid=user,
        configuration='{"some": "config", "dict": "values"}',
        tool="dummytool",
        slurm_output="/path/to/slurm-44742.out",
        host=socket.gethostbyname(socket.gethostname()),
    )
    yield user, hist
    user.delete()
    hist


@pytest.fixture(scope="function")
def temp_user(dummy_settings):
    from evaluation_system.tests.mocks.dummy import DummyUser
    import evaluation_system.api.plugin_manager as pm

    with DummyUser(random_home=True, pw_name=getuser()) as user:
        yield user


@pytest.fixture(scope="function")
def dummy_user(
    dummy_env, dummy_settings, config_dict, dummy_plugin, dummy_history, temp_user
):

    from django.contrib.auth.models import User

    User.objects.filter(username="test_user2").delete()
    user_entry = namedtuple("test_user2", ["user", "row_id", "username"])
    user_entry.user = temp_user
    user_entry.username = "test_user2"
    user_entry.row_id = temp_user.getUserDB().storeHistory(
        dummy_plugin,
        config_dict,
        user_entry.username,
        dummy_history.processStatus.not_scheduled,
        caption="My caption",
    )
    yield user_entry
    User.objects.filter(username=user_entry.username).delete()


@pytest.fixture(scope="module")
def config_dict():
    yield {
        "the_number": 42,
        "number": 12,
        "something": "else",
        "other": "value",
        "input": "/folder",
        "variable": "pr",
    }


@pytest.fixture(scope="module")
def tmp_dir():
    with TemporaryDirectory(prefix="freva_test_") as td:
        yield Path(td)
        [f.unlink() for f in Path(td).rglob("*.*")]


@pytest.fixture(scope="module")
def search_dict():
    yield {
        "variable": "tas",
        "project": "CMIP5",
        "product": "output1",
        "time_frequency": "mon",
        "experiment": "decadal2000",
        "model": "MPI-ESM-LR",
        "ensemble": "r1i1p1",
    }


@pytest.fixture(scope="module")
def dummy_settings_single(dummy_env):
    # Application definition
    import evaluation_system.settings.database
    from evaluation_system.misc import config

    config.reloadConfiguration()
    yield config


@pytest.fixture(scope="session")
def dummy_settings(dummy_env):
    from evaluation_system.misc import config

    config.reloadConfiguration()
    import evaluation_system.settings.database

    yield config


@pytest.fixture(scope="function")
def root_path_with_empty_config(dummy_env):
    from evaluation_system.misc import config

    root_path = Path(config.get_drs_config()["crawl_my_data"]["root_dir"])
    crawl_dir = root_path / f"user-{getuser()}" / "freva-ces-plugin-results"
    config._config = {}
    yield crawl_dir
    config.reloadConfiguration()


@pytest.fixture(scope="module")
def hist_obj(django_user):

    from evaluation_system.model.history.models import History
    from django.contrib.auth.models import User
    from evaluation_system.misc import config

    yield History.objects.create(
        status=History.processStatus.running,
        slurm_output="/some/out.txt",
        host=socket.gethostbyname(socket.gethostname()),
        timestamp=datetime.datetime.now(),
        uid=User.objects.first(),
    )
    config.reloadConfiguration()
