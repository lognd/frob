"""Tests for PKG001/PKG002/PKG003 (T-4219): a relative embedded-image
reference in markdown mis-renders on a consumer with no repository
context (a package index rendering the declared long description, most
concretely)."""

from __future__ import annotations

from pathlib import Path

from frob.findings import Severity
from frob.gates import pkg_resources_gate


def _rules(violations) -> set[str]:
    """Every distinct `Violation.rule` id in `violations`."""
    return {v.rule for v in violations}


def _write(path: Path, content: str) -> None:
    """Write `content` to `path` (parents created as needed) -- the one
    filesystem-write funnel every test fixture in this module goes
    through, so `SELFAUDIT001`/`SYS100` has a single site to account for
    rather than one per call."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_pyproject(root: Path, *, readme: str | None = "README.md") -> None:
    """A minimal pyproject.toml declaring (or, if `readme` is None,
    omitting) `[project].readme`."""
    readme_line = f'readme = "{readme}"\n' if readme is not None else ""
    _write(
        root / "pyproject.toml",
        f'[project]\nname = "sample"\nversion = "0.1.0"\n{readme_line}',
    )


class TestPkg001DeclaredLongDescription:
    """PKG001: a relative image source in the declared long-description
    file is an ERROR -- the MUST-FIRE fixture from T-4219's own body."""

    def test_relative_markdown_image_in_declared_readme_fires_error(
        self, tmp_path: Path
    ) -> None:
        # frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
        # frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg001DeclaredLongDescription.test_relative_markdown_image_in_declared_readme_fires_error  # noqa: E501
        root = tmp_path / "repo"
        _write_pyproject(root)
        _write(root / "README.md", "# Sample\n\n![banner](docs/assets/banner.svg)\n")
        violations = pkg_resources_gate(root)
        pkg001 = [v for v in violations if v.rule == "PKG001"]
        assert len(pkg001) == 1
        assert pkg001[0].severity == Severity.ERROR
        assert pkg001[0].file == "README.md"
        assert "docs/assets/banner.svg" in pkg001[0].message

    def test_relative_html_img_src_in_declared_readme_fires_error(
        self, tmp_path: Path
    ) -> None:
        # frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
        # frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg001DeclaredLongDescription.test_relative_html_img_src_in_declared_readme_fires_error  # noqa: E501
        root = tmp_path / "repo"
        _write_pyproject(root)
        _write(
            root / "README.md",
            '<p align="center">\n'
            '  <img src="docs/assets/banner.svg" alt="banner" width="100%"/>\n'
            "</p>\n",
        )
        violations = pkg_resources_gate(root)
        pkg001 = [v for v in violations if v.rule == "PKG001"]
        assert len(pkg001) == 1
        assert pkg001[0].severity == Severity.ERROR

    # frob:waive DUP002 reason="near-identical to \
    # test_image_inside_code_span_does_not_fire -- distinct MUST-STAY-QUIET fixtures \
    # sharing one arrange/act/assert shape, T-4219"
    def test_absolute_image_source_does_not_fire(self, tmp_path: Path) -> None:
        # frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
        # frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg001DeclaredLongDescription.test_absolute_image_source_does_not_fire  # noqa: E501
        root = tmp_path / "repo"
        _write_pyproject(root)
        _write(
            root / "README.md",
            "# Sample\n\n![banner](https://raw.githubusercontent.com/o/r/main/b.svg)\n",
        )
        violations = pkg_resources_gate(root)
        assert "PKG001" not in _rules(violations)

    def test_relative_link_target_in_declared_readme_does_not_fire(
        self, tmp_path: Path
    ) -> None:
        # frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
        # frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg001DeclaredLongDescription.test_relative_link_target_in_declared_readme_does_not_fire  # noqa: E501
        """MUST-STAY-QUIET (T-4219): a relative LINK target -- not an
        embedded resource -- in the declared long description reports
        nothing, ever, per the owner's explicit narrowing to resources
        only."""
        root = tmp_path / "repo"
        _write_pyproject(root)
        _write(
            root / "README.md",
            '# Sample\n\n<a href="LICENSE">License</a>\n\n[license](LICENSE)\n',
        )
        violations = pkg_resources_gate(root)
        assert violations == ()

    def test_image_inside_code_span_does_not_fire(self, tmp_path: Path) -> None:
        # frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
        # frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg001DeclaredLongDescription.test_image_inside_code_span_does_not_fire  # noqa: E501
        root = tmp_path / "repo"
        _write_pyproject(root)
        _write(
            root / "README.md",
            "# Sample\n\nExample syntax: `![alt](docs/assets/banner.svg)`\n",
        )
        violations = pkg_resources_gate(root)
        assert "PKG001" not in _rules(violations)


class TestPkg002NonDeclaredMarkdown:
    """PKG002: the same finding in a non-declared markdown file is a
    WARNING, never an error -- the MUST-STAY-QUIET severity fixture."""

    def test_relative_image_in_other_markdown_warns_not_errors(
        self, tmp_path: Path
    ) -> None:
        # frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
        # frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg002NonDeclaredMarkdown.test_relative_image_in_other_markdown_warns_not_errors  # noqa: E501
        root = tmp_path / "repo"
        _write_pyproject(root)
        _write(root / "README.md", "# Sample\n")
        _write(
            root / "docs" / "guide.md", "# Guide\n\n![diagram](assets/diagram.png)\n"
        )
        violations = pkg_resources_gate(root)
        pkg002 = [v for v in violations if v.rule == "PKG002"]
        assert len(pkg002) == 1
        assert pkg002[0].severity == Severity.WARN
        assert pkg002[0].file == "docs/guide.md"
        assert "PKG001" not in _rules(violations)

    def test_declared_readme_is_not_double_reported_as_pkg002(
        self, tmp_path: Path
    ) -> None:
        # frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
        # frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg002NonDeclaredMarkdown.test_declared_readme_is_not_double_reported_as_pkg002  # noqa: E501
        root = tmp_path / "repo"
        _write_pyproject(root)
        _write(root / "README.md", "# Sample\n\n![banner](docs/assets/banner.svg)\n")
        violations = pkg_resources_gate(root)
        assert len(violations) == 1
        assert violations[0].rule == "PKG001"


class TestPkg003NoDeclaredLongDescription:
    """PKG003: a project declaring no long-description file is handled
    explicitly (UNRESOLVED), never a crash and never a silent pass --
    the THIRD fixture from T-4219's own body."""

    def test_no_readme_key_reports_unresolved_not_a_crash_or_silent_pass(
        self, tmp_path: Path
    ) -> None:
        # frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
        # frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg003NoDeclaredLongDescription.test_no_readme_key_reports_unresolved_not_a_crash_or_silent_pass  # noqa: E501
        root = tmp_path / "repo"
        _write_pyproject(root, readme=None)
        _write(root / "README.md", "# Sample\n\n![banner](docs/assets/banner.svg)\n")
        violations = pkg_resources_gate(root)
        pkg003 = [v for v in violations if v.rule == "PKG003"]
        assert len(pkg003) == 1
        assert pkg003[0].severity == Severity.UNRESOLVED
        # PKG001 must not silently substitute the conventional filename.
        assert "PKG001" not in _rules(violations)

    def test_missing_pyproject_reports_unresolved(self, tmp_path: Path) -> None:
        # frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
        # frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg003NoDeclaredLongDescription.test_missing_pyproject_reports_unresolved  # noqa: E501
        root = tmp_path / "repo"
        root.mkdir()
        violations = pkg_resources_gate(root)
        assert _rules(violations) == {"PKG003"}


class TestPkg001RemedyMessage:
    """The remedy clause derives a concrete raw-content URL when the
    manifest declares a recognized forge repository, and otherwise states
    only the remedy's shape -- T-4219's explicit "never guess" rule."""

    def test_remedy_derives_raw_url_from_declared_repository(
        self, tmp_path: Path
    ) -> None:
        # frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
        # frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg001RemedyMessage.test_remedy_derives_raw_url_from_declared_repository  # noqa: E501
        root = tmp_path / "repo"
        _write(
            root / "pyproject.toml",
            '[project]\nname = "sample"\nversion = "0.1.0"\n'
            'readme = "README.md"\n\n'
            "[project.urls]\n"
            'Homepage = "https://github.com/lognd/frob"\n',
        )
        _write(root / "README.md", "# Sample\n\n![banner](docs/assets/banner.svg)\n")
        violations = pkg_resources_gate(root)
        pkg001 = [v for v in violations if v.rule == "PKG001"][0]
        assert "raw.githubusercontent.com/lognd/frob" in pkg001.message, pkg001.message

    # frob:waive DUP002 reason="near-identical to \
    # test_relative_markdown_image_in_declared_readme_fires_error -- same fixture, one \
    # asserts the finding, the other the remedy shape, T-4219"
    def test_remedy_states_shape_only_with_no_declared_repository(
        self, tmp_path: Path
    ) -> None:
        # frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
        # frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg001RemedyMessage.test_remedy_states_shape_only_with_no_declared_repository  # noqa: E501
        root = tmp_path / "repo"
        _write_pyproject(root)
        _write(root / "README.md", "# Sample\n\n![banner](docs/assets/banner.svg)\n")
        violations = pkg_resources_gate(root)
        pkg001 = [v for v in violations if v.rule == "PKG001"][0]
        assert "raw.githubusercontent.com" not in pkg001.message
        assert "host, owner" in pkg001.message
