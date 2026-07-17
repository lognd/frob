"""Unit tests for frob.vet: lockfile parsers, allow conformance, quarantine,
typosquat, and hook-command parsing (docs/vet.md). No real network calls."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from frob.vet._allow import load_vet_config
from frob.vet._hook import check_package, parse_hook_command
from frob.vet._lockfile import find_lockfile, parse_lockfile
from frob.vet._models import Dependency
from frob.vet._registry import RegistryResult
from frob.vet._typosquat import damerau_levenshtein, find_typosquat

# ---------------------------------------------------------------------------
# lockfile parsers
# ---------------------------------------------------------------------------

UV_LOCK = """\
version = 1
requires-python = ">=3.11"

[[package]]
name = "requests"
version = "2.31.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "idna"
version = "3.6"
source = { registry = "https://pypi.org/simple" }
"""

PACKAGE_LOCK_JSON_V3 = json.dumps(
    {
        "name": "app",
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "app", "version": "1.0.0"},
            "node_modules/lodash": {"version": "4.17.21"},
            "node_modules/chalk": {"version": "5.3.0"},
        },
    }
)

PACKAGE_LOCK_JSON_V1 = json.dumps(
    {
        "name": "app",
        "lockfileVersion": 1,
        "dependencies": {
            "express": {"version": "4.18.2"},
        },
    }
)

PNPM_LOCK_YAML = """\
lockfileVersion: '6.0'

packages:
  /lodash@4.17.21:
    resolution: {integrity: sha512-xyz}
  /chalk@5.3.0:
    resolution: {integrity: sha512-abc}
"""

CARGO_LOCK = """\
version = 3

[[package]]
name = "serde"
version = "1.0.195"

[[package]]
name = "tokio"
version = "1.35.1"
"""


class TestLockfileParsers:
    def test_find_lockfile_uv(self, tmp_path: Path) -> None:
        (tmp_path / "uv.lock").write_text(UV_LOCK)
        assert find_lockfile(tmp_path) == tmp_path / "uv.lock"

    def test_find_lockfile_none(self, tmp_path: Path) -> None:
        assert find_lockfile(tmp_path) is None

    def test_parse_uv_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "uv.lock"
        path.write_text(UV_LOCK)
        result = parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="pypi", name="requests", version="2.31.0") in deps
        assert len(deps) == 2

    def test_parse_package_lock_json_v3(self, tmp_path: Path) -> None:
        path = tmp_path / "package-lock.json"
        path.write_text(PACKAGE_LOCK_JSON_V3)
        result = parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="lodash", version="4.17.21") in deps
        assert Dependency(ecosystem="npm", name="chalk", version="5.3.0") in deps

    def test_parse_package_lock_json_v1(self, tmp_path: Path) -> None:
        path = tmp_path / "package-lock.json"
        path.write_text(PACKAGE_LOCK_JSON_V1)
        result = parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="express", version="4.18.2") in deps

    def test_parse_pnpm_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "pnpm-lock.yaml"
        path.write_text(PNPM_LOCK_YAML)
        result = parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="lodash", version="4.17.21") in deps

    def test_parse_cargo_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "Cargo.lock"
        path.write_text(CARGO_LOCK)
        result = parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="cargo", name="serde", version="1.0.195") in deps

    def test_unsupported_lockfile(self, tmp_path: Path) -> None:
        path = tmp_path / "yarn.lock"
        result = parse_lockfile(path)
        assert result.is_err

    def test_malformed_uv_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "uv.lock"
        path.write_text("not valid = [ toml")
        result = parse_lockfile(path)
        assert result.is_err


# ---------------------------------------------------------------------------
# allow conformance / config loading
# ---------------------------------------------------------------------------


class TestAllowConfig:
    def test_no_frob_toml_is_advisory_only(self, tmp_path: Path) -> None:
        cfg = load_vet_config(tmp_path)
        assert cfg.present is False

    def test_no_vet_section_is_advisory_only(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text("check_base = 'main'\n")
        cfg = load_vet_config(tmp_path)
        assert cfg.present is False

    def test_vet_section_present(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text(
            """
[vet]
enforce = true
osv = false
quarantine_days = 7

[vet.allow]
requests = true
jinja2 = ["sandboxed template compilation, reviewed"]
"""
        )
        cfg = load_vet_config(tmp_path)
        assert cfg.present is True
        assert cfg.enforce is True
        assert cfg.quarantine_days == 7
        assert cfg.allow["requests"] is True
        assert cfg.allow["jinja2"] == ("sandboxed template compilation, reviewed",)


# ---------------------------------------------------------------------------
# quarantine logic (monkeypatched registry)
# ---------------------------------------------------------------------------


class TestQuarantine:
    def test_fresh_package_blocked(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from frob.vet import _registry

        def fake_fetch(ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0):
            return RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=2),
                resolved_version=version,
            )

        monkeypatch.setattr(_registry, "fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "some-new-pkg", "1.0.0", root=tmp_path)
        assert verdict.verdict == "quarantine"
        assert verdict.blocked is True

    def test_old_package_ok(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from frob.vet import _registry

        def fake_fetch(ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0):
            return RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=900),
                resolved_version=version,
            )

        monkeypatch.setattr(_registry, "fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "requests", "2.31.0", root=tmp_path)
        assert verdict.verdict == "ok"
        assert verdict.blocked is False

    def test_network_failure_degrades_to_unverified(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.vet import _registry

        def fake_fetch(ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0):
            return RegistryResult(ok=False, note="could not verify publish date: timeout")

        monkeypatch.setattr(_registry, "fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "requests", "2.31.0", root=tmp_path)
        assert verdict.verdict == "unverified"
        assert verdict.blocked is False


# ---------------------------------------------------------------------------
# typosquat
# ---------------------------------------------------------------------------


class TestTyposquat:
    def test_damerau_levenshtein_basic(self) -> None:
        assert damerau_levenshtein("requests", "requests") == 0
        assert damerau_levenshtein("requets", "requests") == 1
        assert damerau_levenshtein("laodash", "lodash") == 1

    def test_requets_flags_requests(self) -> None:
        assert find_typosquat("pypi", "requets") == "requests"

    def test_laodash_flags_lodash(self) -> None:
        assert find_typosquat("npm", "laodash") == "lodash"

    def test_known_popular_package_not_flagged(self) -> None:
        assert find_typosquat("pypi", "requests") is None

    def test_unrelated_name_not_flagged(self) -> None:
        assert find_typosquat("pypi", "some-totally-unrelated-package-xyz") is None


# ---------------------------------------------------------------------------
# hook-command parsing table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("uv add requests", ("pypi", (("requests", ""),))),
        ("uv add requests==2.31.0", ("pypi", (("requests", "2.31.0"),))),
        ("uv pip install requests", ("pypi", (("requests", ""),))),
        ("pip install requests==2.31.0", ("pypi", (("requests", "2.31.0"),))),
        ("pip3 install foo bar", ("pypi", (("foo", ""), ("bar", "")))),
        ("npm install lodash", ("npm", (("lodash", ""),))),
        ("npm i chalk@5.0.0", ("npm", (("chalk", "5.0.0"),))),
        ("pnpm add express", ("npm", (("express", ""),))),
        ("yarn add react react-dom", ("npm", (("react", ""), ("react-dom", "")))),
        (
            "npx some-plausible-nonexistent-name-2026",
            ("npm", (("some-plausible-nonexistent-name-2026", ""),)),
        ),
        ("cargo add serde@1.0", ("cargo", (("serde", "1.0"),))),
        ("cargo add serde", ("cargo", (("serde", ""),))),
        ("npm install --save-dev lodash", ("npm", (("lodash", ""),))),
        ("git status", None),
        ("ls -la", None),
        ("echo hello", None),
        ("", None),
    ],
)
def test_parse_hook_command(command: str, expected) -> None:
    assert parse_hook_command(command) == expected


def test_parse_hook_command_scoped_npm_package() -> None:
    result = parse_hook_command("npm install @babel/core@7.23.0")
    assert result == ("npm", (("@babel/core", "7.23.0"),))
