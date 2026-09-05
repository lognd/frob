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
