"""Tests for T-4650's registry-file class
(docs/modules/tickets.md#registry-files-append-shared-t-draft-a62505d4):
`frob.tickets._registry_files` (the config-driven path set and the pure
additive-diff-text scan), `scope_matches`'s implicit-scope rule for the
default set (acceptance a), and `frob.tickets._land.
_registry_file_diff_is_additive`/`_registry_leakage_exempt_paths` (the
CrossTicketLeakage exemption, acceptances b and c)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.tickets._land import (
    _registry_file_diff_is_additive,
    _registry_leakage_exempt_paths,
)
from frob.tickets._models import scope_matches
from frob.tickets._registry_files import (
    DEFAULT_REGISTRY_FILES,
    is_additive_diff_text,
    is_registry_file,
    registry_files,
)


def _run(argv: list[str], cwd: Path) -> None:
    subprocess.run(argv, cwd=str(cwd), check=True, capture_output=True, text=True)


def _git_repo(tmp_path: Path) -> Path:
    """A real git checkout with one committed file, `main` as the default
    branch -- the shared fixture shape `_registry_file_diff_is_additive`/
    `_registry_leakage_exempt_paths` both need a real diff to measure."""
    _run(["git", "init", "-b", "main"], tmp_path)
    _run(["git", "config", "user.email", "t@example.com"], tmp_path)
    _run(["git", "config", "user.name", "T"], tmp_path)
    (tmp_path / "docs" / "modules").mkdir(parents=True)
    reg = tmp_path / "docs" / "modules" / "gates.md"
    reg.write_text("# gates\n\n| rule | file |\n|---|---|\n")
    _run(["git", "add", "."], tmp_path)
    _run(["git", "commit", "-m", "init"], tmp_path)
    return tmp_path


class TestRegistryFiles:
    """`registry_files`/`is_registry_file` (T-4650)."""

    # frob:tests src/frob/tickets/_registry_files.py::registry_files
    def test_no_root_returns_default(self) -> None:
        """`registry_files(None)` returns the documented default set."""
        assert registry_files(None) == DEFAULT_REGISTRY_FILES
# frob:tests src/frob/tickets/_registry_files.py::registry_files

    def test_no_frob_toml_returns_default(self, tmp_path: Path) -> None:
        """A repo root with no `frob.toml` at all falls back to default."""
        assert registry_files(tmp_path) == DEFAULT_REGISTRY_FILES

    # frob:tests src/frob/tickets/_registry_files.py::registry_files
    def test_configured_override_replaces_default(self, tmp_path: Path) -> None:
        """`[tickets].registry_files` in `frob.toml` replaces the default
        set entirely, honoring the ticket's "configured in frob.toml"
        requirement."""
        (tmp_path / "frob.toml").write_text(
            '[tickets]\nregistry_files = ["some/custom/registry.yaml"]\n'
        )
        assert registry_files(tmp_path) == frozenset({"some/custom/registry.yaml"})

    # frob:tests src/frob/tickets/_registry_files.py::registry_files
    def test_malformed_value_falls_back_to_default(self, tmp_path: Path) -> None:
        """A non-list `registry_files` value degrades to the default
        rather than crashing or silently emptying the set."""
        (tmp_path / "frob.toml").write_text('[tickets]\nregistry_files = "oops"\n')
        assert registry_files(tmp_path) == DEFAULT_REGISTRY_FILES

    # frob:tests src/frob/tickets/_registry_files.py::is_registry_file
    def test_is_registry_file_membership(self) -> None:
        """`is_registry_file` matches the default set's own paths."""
        assert is_registry_file("docs/modules/gates.md", None)
        assert not is_registry_file("src/frob/tickets/_land.py", None)


class TestIsAdditiveDiffText:
    """`is_additive_diff_text` (T-4650 acceptances b/c): the
    # frob:tests src/frob/tickets/_registry_files.py::is_additive_diff_text
    pure, no-subprocess unified-diff scan."""

    # frob:tests src/frob/tickets/_registry_files.py::is_additive_diff_text
    def test_pure_append_is_additive(self) -> None:
        """A diff with only `+` hunk lines (never a bare `-`) is
        additive-only."""
        diff = "@@ -3,0 +4 @@\n+| NEW001 | foo.py |\n"
        assert is_additive_diff_text(diff) is True

    # frob:tests src/frob/tickets/_registry_files.py::is_additive_diff_text
    def test_deleted_line_is_not_additive(self) -> None:
        """A diff containing a real removed line (`-`, not `---`) is NOT
        additive-only."""
        diff = "@@ -3,1 +3,0 @@\n-|---|---|\n"
        assert is_additive_diff_text(diff) is False

    # frob:tests src/frob/tickets/_registry_files.py::is_additive_diff_text
    def test_file_header_dashes_are_not_removed_lines(self) -> None:
        """The `---`/`+++` file-header lines never count as a removal."""
        diff = "--- a/docs/modules/gates.md\n+++ b/docs/modules/gates.md\n+added\n"
        assert is_additive_diff_text(diff) is True

    # frob:tests src/frob/tickets/_registry_files.py::is_additive_diff_text
    def test_empty_diff_is_additive(self) -> None:
        """No diff at all (identical content) is vacuously additive-only."""
        assert is_additive_diff_text("") is True


class TestRegistryFileDiffIsAdditive:
    """`frob.tickets._land._registry_file_diff_is_additive`
    (T-4650 acceptances b/c): the real-git-spawn half that
    feeds `is_additive_diff_text`."""

    def test_pure_append_is_additive(self, tmp_path: Path) -> None:
        """A branch that only appends a new line to the registry file
        diffs as additive-only."""
        repo = _git_repo(tmp_path)
        reg = repo / "docs" / "modules" / "gates.md"
        reg.write_text(reg.read_text() + "| NEW001 | foo.py |\n")
        _run(["git", "commit", "-am", "add NEW001"], repo)
        assert (
            _registry_file_diff_is_additive(repo, "HEAD~1", "docs/modules/gates.md")
            is True
        )

    def test_deleted_line_is_not_additive(self, tmp_path: Path) -> None:
        """A branch that removes an existing line diffs as NOT
        additive-only, even if it also adds a line elsewhere."""
        repo = _git_repo(tmp_path)
        reg = repo / "docs" / "modules" / "gates.md"
        reg.write_text("# gates\n\n| rule | file |\n")  # dropped the "|---|---|" row
        _run(["git", "commit", "-am", "drop a row"], repo)
        assert (
            _registry_file_diff_is_additive(repo, "HEAD~1", "docs/modules/gates.md")
            is False
        )

    def test_bad_ref_fails_closed(self, tmp_path: Path) -> None:
        """An unresolvable `base_ref` is treated as NOT additive-only
        (fail closed), never silently exempted."""
        repo = _git_repo(tmp_path)
        assert (
            _registry_file_diff_is_additive(
                repo, "not-a-real-ref", "docs/modules/gates.md"
            )
            is False
        )


# frob:ticket T-4650
class TestScopeMatchesRegistryImplicit:
    """`scope_matches`'s implicit registry-file coverage (T-4650
    acceptance a): mirrors `LEDGER_PATH`'s always-in-scope rule."""

    # frob:tests src/frob/tickets/_models.py::scope_matches
    def test_registry_file_matches_with_empty_scope(self) -> None:
        """A ticket with NO declared scope at all still matches a
        registry file -- no `--add`, no lease, ever required."""
        assert scope_matches("docs/modules/gates.md", ())

    # frob:tests src/frob/tickets/_models.py::scope_matches
    def test_registry_file_matches_with_unrelated_scope(self) -> None:
        """A ticket whose declared scope covers something unrelated still
        matches every default registry file."""
        for path in DEFAULT_REGISTRY_FILES:
            assert scope_matches(path, ("src/frob/unrelated_module.py",))

    def test_non_registry_file_still_requires_declared_scope(self) -> None:
        """An ordinary file is unaffected by the registry-file rule --
        still requires actual scope coverage."""
        assert not scope_matches("src/frob/unrelated_module.py", ())


class TestRegistryLeakageExemptPaths:
    """`frob.tickets._land._registry_leakage_exempt_paths`
    (T-4650 acceptances b/c): the CrossTicketLeakage exemption
    wiring."""

    # frob:tests src/frob/tickets/_land.py::_check_cross_ticket_leakage
    def test_additive_registry_change_is_exempt(self, tmp_path: Path) -> None:
        """A registry file changed only additively on this branch is
        dropped from the leakage-relevant set."""
        repo = _git_repo(tmp_path)
        reg = repo / "docs" / "modules" / "gates.md"
        reg.write_text(reg.read_text() + "| NEW002 | bar.py |\n")
        _run(["git", "commit", "-am", "add NEW002"], repo)
        exempt = _registry_leakage_exempt_paths(
            repo, "HEAD~1", frozenset({"docs/modules/gates.md"})
        )
        assert exempt == frozenset({"docs/modules/gates.md"})

    # frob:tests src/frob/tickets/_land.py::_check_cross_ticket_leakage
    def test_destructive_registry_change_is_not_exempt(self, tmp_path: Path) -> None:
        """A registry file whose diff deletes/rewrites an existing line
        is NEVER exempted -- CrossTicketLeakage must still be free to
        refuse on it (acceptance c)."""
        repo = _git_repo(tmp_path)
        reg = repo / "docs" / "modules" / "gates.md"
        reg.write_text("# gates\n\n| rule | file |\n")
        _run(["git", "commit", "-am", "drop a row"], repo)
        exempt = _registry_leakage_exempt_paths(
            repo, "HEAD~1", frozenset({"docs/modules/gates.md"})
        )
        assert exempt == frozenset()

    def test_non_registry_path_is_never_exempt(self, tmp_path: Path) -> None:
        """A changed path that is not a configured registry file at all
        is never included, regardless of its diff shape."""
        repo = _git_repo(tmp_path)
        src = repo / "src.py"
        src.write_text("x = 1\n")
        _run(["git", "add", "."], repo)
        _run(["git", "commit", "-m", "add src"], repo)
        exempt = _registry_leakage_exempt_paths(repo, "HEAD~1", frozenset({"src.py"}))
        assert exempt == frozenset()
