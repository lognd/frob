"""Mechanical proof of the post-alpha branch flow (docs/guides/release.md
"Branch flow after the alpha"): every ticket lands onto `dev`, CI runs on
`dev` as well as `main`, and the per-land dev-version bump is back on.
Parses the REAL `pyproject.toml` and `ci.yml` in this repo, not fixture
copies, so a regression here means the live configuration drifted."""

from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"

# PyYAML reads the workflow's `on:` key as the boolean True (YAML 1.1 alias).
_ON_KEY = True


def _tool_frob() -> dict:
    """The live `[tool.frob]` table, failing loudly if it is absent."""
    with _PYPROJECT.open("rb") as f:
        doc = tomllib.load(f)
    table = doc.get("tool", {}).get("frob")
    assert isinstance(table, dict), "pyproject.toml has no [tool.frob] table"
    return table


def test_land_target_is_dev() -> None:
    """The land target default is `dev`, so a land run without `--onto`
    from a root checked out on `dev` never publishes onto the frozen
    `main`."""
    assert _tool_frob().get("ticket_land_branch") == "dev"


def test_dev_version_bump_is_on() -> None:
    """Between release cuts the per-land dev-version bump is on, so a dev
    build never shares its version identity with the published final."""
    assert _tool_frob().get("dev_version_bump") is True


def test_ci_runs_on_dev_and_main() -> None:
    """`ci.yml` triggers on pushes to both `main` and `dev`: the dev branch
    carries its own full-matrix green reading before it is merged."""
    with _CI_WORKFLOW.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    branches = doc[_ON_KEY]["push"]["branches"]
    assert set(branches) >= {"main", "dev"}, branches
