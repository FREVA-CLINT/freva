import os
import pytest
import mock

SUBCOMMANDS = ("databrowser", "esgf", "user-data", "history", "plugin")


def test_main_complete(dummy_env, capsys):

    from freva.cli.utils import print_choices

    print_choices(["freva"])
    sub_commands = capsys.readouterr().out
    for subcommand in SUBCOMMANDS:
        assert subcommand in sub_commands
    print_choices(["--shell", "tcsh", "freva"])
    assert capsys.readouterr().out == sub_commands
    print_choices(["--shell", "zsh", "freva"])
    sub_commands_zsh = capsys.readouterr().out.split("\n")
    for complete in [s.strip() for s in sub_commands_zsh if s.strip()]:
        cmd = complete.split("[")
        assert cmd[0] in SUBCOMMANDS
        assert len(cmd) == 2
    print_choices(["--shell", "fish", "freva"])
    sub_commands_fish = capsys.readouterr().out.split("\n")
    for complete in [s.strip() for s in sub_commands_fish if s.strip()]:
        cmd = complete.split(":")
        assert cmd[0] in SUBCOMMANDS
        assert len(cmd) == 2


def test_subcommand_help(dummy_env, capsys):

    from freva.cli.utils import print_choices
    from freva.cli import main as main_cli

    for subcmd in SUBCOMMANDS:
        with pytest.raises(SystemExit):
            main_cli([subcmd, "--help"])
        doc_string = capsys.readouterr().out
        for shell, sep in {"bash": "", "zsh": "[", "fish": ":"}.items():
            print_choices(["--shell", shell, "--flags-only", f"freva-{subcmd}"])
            choices = capsys.readouterr().out.split("\n")
            for choice in [s.strip() for s in choices if s.strip()]:
                if sep:
                    cmd, _, help = choice.partition(sep)
                    help = help.rstrip("]")
                else:
                    cmd = choice
                    help = ""
                assert cmd in doc_string
                assert cmd.startswith("-")
                if help:
                    # The 20 first characters should be ok for this comparison
                    assert help[:20] in doc_string
            if subcmd not in ("databrowser", "plugin"):
                print_choices(["--shell", shell, "--strip", f"freva-{subcmd}"])
                out = [
                    s.strip() for s in capsys.readouterr().out.split("\n") if s.strip()
                ]
                if subcmd == "user-data":
                    assert len(out) == 3
                else:
                    assert len(out) == 0


def test_databrowser(dummy_env, capsys, dummy_solr):

    from freva.cli.utils import print_choices
    from freva.cli import main as main_cli

    main_cli(["databrowser", "--all-facets"])
    facets = capsys.readouterr().out
    for shell in ("bash", "zsh", "fish"):
        print_choices(["--shell", shell, "--strip", "freva", "databrowser"])
        choices = capsys.readouterr().out
        assert choices == facets
        print_choices(
            ["--shell", shell, "--strip", "freva", "databrowser", "time_frequency=mon"]
        )
        choices = capsys.readouterr().out
        assert "time_frequency" not in choices


def test_plugin(dummy_env, capsys):

    from freva.cli.utils import print_choices
    from freva._plugin import _write_plugin_cache
    from freva.cli import main as main_cli

    _write_plugin_cache()

    for shell in ("bash", "zsh", "fish"):
        print_choices(["--shell", shell, "--strip", "freva", "plugin"])
        choices = capsys.readouterr().out
        assert "dummyplugin" in choices
        print_choices(["--shell", shell, "--strip", "freva", "plugin", "dummyplugin"])
        choices = capsys.readouterr().out
        assert "the_number" in choices
        print_choices(
            [
                "--shell",
                shell,
                "--strip",
                "freva",
                "plugin",
                "dummyplugin",
                "the_number=1",
            ]
        )
        choices = capsys.readouterr().out
        assert "the_number" not in choices


def test_wrong_choice(dummy_env, capsys):

    from freva.cli.utils import print_choices
    from freva.cli import main as main_cli

    for shell in ("bash", "zsh", "fish"):
        for cmd in (["solr"], ["plugin", "nplg"]):
            print_choices(["--shell", shell, "--strip", "freva"] + cmd)
            choices = capsys.readouterr().out
            assert len(choices) == 0
