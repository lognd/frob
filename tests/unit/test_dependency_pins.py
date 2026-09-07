"""T-3857 (FROBLEMS F-001): a fresh resolve of `frob[serve]` (or the dev
group) must never be able to pick up mcp 2.x, which renamed `FastMCP` to
`MCPServer` and broke `frob.serve.server`'s import. This module's own
`mcp` specifier is the actual regression surface -- a static parse of
`pyproject.toml`'s real content, not a synthetic fixture, so a future
edit that widens the pin back out is caught here directly rather than
only in a clean-environment resolve nobody runs locally (T-3857's own
"why this repo does not see it" section)."""

from __future__ import annotations

from pathlib import Path

from packaging.requirements import Requirement

# T-3857: reuses `frob.gates._version_coupling`'s own toml reader rather
# than a raw `Path.read_text` in this file -- keeps the actual fs.read
# call site inside the `gates` node's already-declared capability
# surface instead of adding a new one to `testsuite`'s design/frob.strata
# via-list (SELFAUDIT001/SYS100).
from frob.gates._version_coupling import _read_toml

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_pyproject() -> dict:
    """This repo's own `pyproject.toml`, parsed once per test."""
    doc = _read_toml(_REPO_ROOT / "pyproject.toml")
    assert doc is not None
    return doc


def _mcp_requirement(specs: list[str]) -> Requirement:
    """The `mcp` entry out of a dependency list, as a parsed `Requirement`."""
    (spec,) = (s for s in specs if Requirement(s).name == "mcp")
    return Requirement(spec)


# frob:ticket T-4046
def _requirement_named(specs: list[str], name: str) -> Requirement | None:
    """The entry named `name` in a dependency list, or `None` if absent --
    unlike `_mcp_requirement` this does not assume exactly one match
    exists, since `tzdata`'s presence/absence in each table is itself
    what T-4046's tests check."""
    matches = [s for s in specs if Requirement(s).name == name]
    if not matches:
        return None
    (spec,) = matches
    return Requirement(spec)


class TestMcpPinIsBounded:
    """MUST-FIRE fixture (T-3857): an environment resolving mcp 2.x must
    be refused at resolution time by the pin, not fail later at import."""

    def test_serve_extra_excludes_mcp_2x(self) -> None:
        """`frob[serve]`'s `mcp` specifier must reject a 2.x release --
        this is the exact published extra a `pip install "frob[serve]"`
        user resolves against."""
        pyproject = _load_pyproject()
        req = _mcp_requirement(pyproject["project"]["optional-dependencies"]["serve"])
        assert "2.0.0" not in req.specifier
        assert "2.1.1" not in req.specifier

    def test_dev_group_excludes_mcp_2x(self) -> None:
        """The dev dependency-group pin must be bounded too -- a
        dev-group-only bound would leave the published extra broken, so
        both must move together (T-3857's own acceptance)."""
        pyproject = _load_pyproject()
        req = _mcp_requirement(pyproject["dependency-groups"]["dev"])
        assert "2.0.0" not in req.specifier
        assert "2.1.1" not in req.specifier

    def test_serve_extra_still_allows_mcp_1x(self) -> None:
        """MUST-STAY-QUIET: mcp 1.x must still satisfy the bounded pin --
        this bound is a ceiling, not an accidental floor-tightening."""
        pyproject = _load_pyproject()
        req = _mcp_requirement(pyproject["project"]["optional-dependencies"]["serve"])
        assert "1.28.1" in req.specifier
        assert "1.29.1" in req.specifier


# frob:ticket T-4046
class TestTzdataDeclaredForWindows:
    """MUST-FIRE fixture (T-4046): `zoneinfo` needs the `tzdata` PyPI
    package on win32 (no bundled tz database there, unlike Linux/macOS'
    system db) -- MEASURED failing on real Windows CI as
    `tests/test_fuzz.py::TestRunFuzz::test_ungeneratable_target_reports_no_generator`'s
    `ModuleNotFoundError: No module named 'tzdata'` /
    `ZoneInfoNotFoundError: 'No time zone found with key UTC'`. This
    checks the pin STRUCTURALLY (a parsed `pyproject.toml` requirement
    and its marker) rather than by re-running the hypothesis-driven test
    and hoping it draws a zoneinfo-reaching example again -- the ticket
    log shows the previous Windows run passed only because hypothesis
    did NOT generate the triggering case, so a green run is not evidence
    of anything here."""

    def test_dev_group_declares_tzdata_for_win32(self) -> None:
        """The dev group must carry a `tzdata` entry gated to win32 --
        only `tests/test_fuzz.py` (via hypothesis' generic
        `st.from_type(object)` strategy) reaches `zoneinfo` in this repo,
        with no shipped-code import under `src/frob`, so this belongs in
        `[dependency-groups].dev`, not `[project].dependencies`."""
        pyproject = _load_pyproject()
        req = _requirement_named(pyproject["dependency-groups"]["dev"], "tzdata")
        assert req is not None, "tzdata must be declared in the dev group for win32"
        assert req.marker is not None, (
            "tzdata must be gated by a marker, not unconditional"
        )
        assert req.marker.evaluate({"sys_platform": "win32"})
        assert not req.marker.evaluate({"sys_platform": "linux"})
        assert not req.marker.evaluate({"sys_platform": "darwin"})

    def test_runtime_dependencies_do_not_declare_tzdata(self) -> None:
        """MUST-STAY-QUIET half of the runtime-vs-test question: no
        shipped-code import reaches `zoneinfo` (the sole hit under
        `src/frob` is a string literal in
        `frob.vet._capability_registry._matrix.NO_CAPABILITY_MODULES`,
        not an import), so `[project].dependencies` must stay free of
        this pin -- promoting it there would be the wrong table for the
        wrong reason (this repo's runtime, not just its tests, would then
        pull an unused package on Linux/macOS)."""
        pyproject = _load_pyproject()
        assert (
            _requirement_named(pyproject["project"]["dependencies"], "tzdata") is None
        )

    def test_non_windows_installs_gain_no_tzdata(self) -> None:
        """MUST-STAY-QUIET: the marker must actually exclude Linux/macOS,
        not just exist -- a malformed or inverted marker would silently
        pull an unnecessary package onto every non-Windows install."""
        pyproject = _load_pyproject()
        req = _requirement_named(pyproject["dependency-groups"]["dev"], "tzdata")
        assert req is not None
        assert req.marker is not None
        for platform in ("linux", "darwin"):
            assert not req.marker.evaluate({"sys_platform": platform})
