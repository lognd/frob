# frob:ticket T-1684
"""Unit tests for the close-time REL001 bump check (T-1684): an
already-applied bump must satisfy it, or no reachable state does."""

from __future__ import annotations

from pathlib import Path

from frob.app.ticket_runner._close_cmd import (
    _declared_pyproject_version,
    _version_covers,
)


class TestDeclaredPyprojectVersion:
    """"Cannot verify" is `None`, never a version that satisfies."""

    def test_absent_pyproject_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestDeclaredPyprojectVersion.test_absent_pyproject_is_none  # noqa: E501
        assert _declared_pyproject_version(tmp_path) is None

    def test_unparsable_pyproject_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestDeclaredPyprojectVersion.test_unparsable_pyproject_is_none  # noqa: E501
        (tmp_path / "pyproject.toml").write_text("[project\n", encoding="utf-8")
        assert _declared_pyproject_version(tmp_path) is None

    def test_reads_the_declared_version(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestDeclaredPyprojectVersion.test_reads_the_declared_version  # noqa: E501
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.356.0"\n', encoding="utf-8"
        )
        assert _declared_pyproject_version(tmp_path) == "0.356.0"


class TestVersionCovers:
    """Numeric dotted comparison; anything else is not satisfied."""

    def test_equal_covers(self) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_equal_covers  # noqa: E501
        assert _version_covers("0.356.0", "0.356.0") is True

    def test_higher_covers(self) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_higher_covers  # noqa: E501
        assert _version_covers("0.357.0", "0.356.0") is True

    def test_lower_does_not_cover(self) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_lower_does_not_cover  # noqa: E501
        assert _version_covers("0.355.0", "0.356.0") is False

    def test_non_numeric_never_covers(self) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_non_numeric_never_covers  # noqa: E501
        assert _version_covers("0.356.0rc1", "0.356.0") is False
