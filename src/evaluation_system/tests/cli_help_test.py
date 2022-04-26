import pytest
import mock
import os

SUBCOMMANDS = ("databrowser", "esgf", "crawl-my-data", "history", "plugin")


def test_main_help(dummy_env, capsys):

    from freva.cli import main as main_cli

    with pytest.raises(SystemExit):
        main_cli(["-h"])
    doc_string = capsys.readouterr().out
    for subcommand in SUBCOMMANDS:
        assert subcommand in doc_string


def test_subcommand_help(dummy_env, capsys):
    from freva.cli import main as main_cli
    from freva.cli.databrowser import main as databrowser
    from freva.cli.esgf import main as esgf
    from freva.cli.plugin import main as plugin
    from freva.cli.history import main as history
    from freva.cli.crawl_my_data import main as crawl_my_data

    functions = (databrowser, esgf, crawl_my_data, history, plugin)
    for subcommand, func in dict(zip(SUBCOMMANDS, functions)).items():
        with pytest.raises(SystemExit):
            func(["--help"])
        doc_string1 = capsys.readouterr().out
        with pytest.raises(SystemExit):
            main_cli([subcommand, "--help"])
        doc_string2 = capsys.readouterr().out
        assert doc_string1 == doc_string2.replace(
            f"freva {subcommand}", f"freva-{subcommand}"
        )
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