"""
Tests for the VWS CLI help.
"""

import pytest
from click.testing import CliRunner
from pytest_regressions.file_regression import FileRegressionFixture

from vws_web_tools import vws_web_tools_group

_SUBCOMMANDS = [[item] for item in vws_web_tools_group.commands]
_BASE_COMMAND: list[list[str]] = [[]]
_COMMANDS = _BASE_COMMAND + _SUBCOMMANDS


@pytest.mark.parametrize(
    argnames="command",
    argvalues=_COMMANDS,
    ids=[str(object=cmd) for cmd in _COMMANDS],
)
def test_vws_command_help(
    command: list[str],
    file_regression: FileRegressionFixture,
) -> None:
    """Expected help text is shown for ``vws`` commands.

    This help text is defined in files.
    To update these files, run ``pytest`` with the ``--regen-all`` flag.
    """
    runner = CliRunner()
    arguments = [*command, "--help"]
    group = vws_web_tools_group
    result = runner.invoke(cli=group, args=arguments, catch_exceptions=False)
    assert result.exit_code == 0
    file_regression.check(contents=result.output)
