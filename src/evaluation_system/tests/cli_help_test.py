from subprocess import run, PIPE, CalledProcessError
import shlex

SUBCOMMANDS = ("databrowser", "esgf", "crawl-my-data", "history", "plugin")


def test_main_help(dummy_env):

    doc_string = run(shlex.split("freva --help"), stdout=PIPE).stdout.decode()
    for subcommand in SUBCOMMANDS:
        assert subcommand in doc_string


def test_subcommand_help(dummy_env):

    for subcommand in SUBCOMMANDS:
        doc_string1 = run(
            shlex.split(f"freva {subcommand} --help"), stdout=PIPE
        ).stdout.decode()
        doc_string2 = run(
            shlex.split(f"freva-{subcommand} --help"), stdout=PIPE
        ).stdout.decode()
        doc_string3 = run(
            shlex.split(f"freva {subcommand[:-1]} --help"), stdout=PIPE, stderr=PIPE
        ).stderr.decode()
        assert doc_string1 == doc_string2.replace(
            f"freva-{subcommand}", f"freva {subcommand}"
        )
        assert subcommand in doc_string3
