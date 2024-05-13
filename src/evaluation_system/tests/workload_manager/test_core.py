import pytest

from evaluation_system.api.workload_manager.core import Job


def test_get_cancel_command():
    from evaluation_system.api.workload_manager import cancel_command

    with pytest.raises(NotImplementedError):
        cancel_command("bla", 1000)
    assert "scancel" in cancel_command("slurm", 1000)


def test_parse_bytes():

    from evaluation_system.api.workload_manager.core import parse_bytes

    assert parse_bytes(123) == 123, "Integer input should return the input as is"

    assert (
        parse_bytes(123.0) == 123
    ), "Float input should return the input converted to int"

    assert (
        parse_bytes("100") == 100
    ), "String input with digits should be correctly parsed"

    assert (
        parse_bytes(" 100 MB ") == 100000000
    ), "String input with spaces should be correctly parsed"

    assert parse_bytes("5kB") == 5000, "String with kB should be correctly parsed"
    assert parse_bytes("1kiB") == 1024, "String with kiB should be correctly parsed"

    assert (
        parse_bytes("MB") == 1000000
    ), "String without digits should prepend '1' and parse correctly"

    try:
        parse_bytes("5 blah")
        assert False, "Expected ValueError for input with invalid units"
    except ValueError as e:
        assert (
            str(e) == "Could not interpret 'blah' as a byte unit"
        ), "Expected specific ValueError message for invalid units"

    try:
        parse_bytes("1e6 blah")
        assert False, "Expected ValueError for malformed number input"
    except ValueError as e:
        assert "Could not interpret" in str(
            e
        ), "Expected ValueError for malformed number input"


def test_string_to_bytes():
    from evaluation_system.api.workload_manager.core import string_to_bytes

    assert (
        string_to_bytes("5g") == 5 * 1000**3
    )  # Specific case when byte_form length is 1


def test_get_format_bytes():
    from evaluation_system.api.workload_manager.core import format_bytes

    assert format_bytes(1) == "1 B", "Failed to format bytes correctly."
    assert format_bytes(1023) == "1.00 kiB", "Failed to format Kibibytes correctly."
    assert format_bytes(1024) == "1.00 kiB", "Failed to format Kibibytes correctly."
    assert format_bytes(2**20) == "1.00 MiB", "Failed to format Mebibytes correctly."
    assert format_bytes(2**30) == "1.00 GiB", "Failed to format Gibibytes correctly."
    assert format_bytes(2**40) == "1.00 TiB", "Failed to format Tebibytes correctly."
    assert format_bytes(2**50) == "1.00 PiB", "Failed to format Pebibytes correctly."
    assert format_bytes(1024 * 1024 - 1) == "1.00 MiB", "Failed on edge of MiB."


class MockJob(Job):
    submit_command = "mock_submit"
    cancel_command = "mock_cancel"

    def __init__(self, *args, **kwargs):
        # For simplicity, bypass Job's __init__ with a direct call to super().__init__()
        # This avoids needing to deal with Job's abstract __init__ parameters.
        super(Job, self).__init__(*args, **kwargs)
        self.job_id = ""  # Ensuring this attribute is set for testing.
        self.name = "mock_job"


# def test_job_methods():

#     job_instance = MockJob()

#     with patch("subprocess.Popen") as mock_popen:
#         mock_process = MagicMock()
#         mock_process.communicate.return_value = (b"output", b"")
#         mock_process.returncode = 0
#         mock_popen.return_value = mock_process

#         output = job_instance._call(["echo", "test"])
#         assert output == "output", "Expected mocked output from _call method."

#     job_id_output = "Submitted batch job 12345"
#     assert (
#         job_instance._job_id_from_submit_output(job_id_output) == "12345"
#     ), "Failed to extract job ID."

#     try:
#         job_instance._job_id_from_submit_output("No job id here")
#     except ValueError as e:
#         assert "Could not parse job id" in str(
#             e
#         ), "Expected failure when job ID is missing."

#     with patch.object(MockJob, "_call", return_value="") as mock_call:
#         job_instance = MockJob()
#         job_instance._close_job("12345", "scancel")
#         mock_call.assert_called_with(["scancel", "12345"])
