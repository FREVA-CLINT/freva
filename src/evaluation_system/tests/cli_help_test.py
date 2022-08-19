import pytest
import mock
import os

SUBCOMMANDS = ("databrowser", "esgf", "user-data", "history", "plugin")


def test_main_help(capsys):

    from freva.cli import main as main_cli

    env = os.environ.copy()
    env.pop("EVALUATION_SYSTEM_CONFIG_FILE", "")
    with mock.patch.dict(os.environ, env, clear=True):
        with pytest.raises(SystemExit):
            main_cli(["-h"])
        doc_string = capsys.readouterr().out
        for subcommand in SUBCOMMANDS:
            assert subcommand in doc_string


def test_subcommand_help(capsys):
    from freva.cli import main as main_cli
    from freva.cli.databrowser import main as databrowser
    from freva.cli.esgf import main as esgf
    from freva.cli.plugin import main as plugin
    from freva.cli.history import main as history
    from freva.cli.user_data import main as user_data

    functions = (databrowser, esgf, user_data, history, plugin)
    env = os.environ.copy()
    env.pop("EVALUATION_SYSTEM_CONFIG_FILE", "")
    with mock.patch.dict(os.environ, env, clear=True):
        for subcommand, func in dict(zip(SUBCOMMANDS, functions)).items():
            with pytest.raises(SystemExit):
                func(["--help"])
            doc_string1 = " ".join(capsys.readouterr().out.replace(" [-V]", "").split())
            with pytest.raises(SystemExit):
                main_cli([subcommand, "--help"])
            doc_string2 = " ".join(
                capsys.readouterr()
                .out.replace(f"freva {subcommand}", f"freva-{subcommand}")
                .split()
            )
            for line in doc_string2.split("\n"):
                print(line)
                assert line.strip() in doc_string1
            with pytest.raises(SystemExit):
                main_cli([subcommand[:-1]])
            doc_string3 = capsys.readouterr().err
            assert subcommand in doc_string3


def test_admin_subcommans_help(admin_env, capsys):
    from evaluation_system.tests import run_cli

    with mock.patch.dict(os.environ, admin_env, clear=True):
        with pytest.raises(SystemExit):
            run_cli("solr")
        assert "the following sub-commands are required:" in capsys.readouterr().err
        with pytest.raises(SystemExit):
            run_cli("check")
        assert "the following sub-commands are required:" in capsys.readouterr().err
