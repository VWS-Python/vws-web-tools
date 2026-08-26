# pyright: reportPrivateUsage=false
# pylint: disable=protected-access
# ruff: noqa: SLF001
"""Tests for XPath string literal quoting."""

import pytest

import vws_web_tools


@pytest.mark.parametrize(
    argnames=("value", "expected"),
    argvalues=[
        ("license", "'license'"),
        ('quotation "marks"', "'quotation \"marks\"'"),
        ("O'Brien", '"O\'Brien"'),
        ("""O'B"n""", 'concat(\'O\', "\'", \'B"n\')'),
        ("""a'b'c"d""", 'concat(\'a\', "\'", \'b\', "\'", \'c"d\')'),
    ],
    ids=[
        "no-quotes",
        "quotation-marks",
        "apostrophe",
        "both-quote-characters",
        "repeated-apostrophes",
    ],
)
def test_xpath_literal(*, value: str, expected: str) -> None:
    """Values are wrapped in quote characters which they do not
    contain.
    """
    assert vws_web_tools._xpath_literal(value=value) == expected
