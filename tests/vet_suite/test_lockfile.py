from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from frob.vet._allow import _load_vet_config
from frob.vet._hook import check_package
from frob.vet._lockfile import _find_lockfile, _parse_lockfile
from frob.vet._models import Dependency
from frob.vet._registry import _RegistryResult
from frob.vet._typosquat import _damerau_levenshtein, _find_typosquat
from tests.conftest import (
    CARGO_LOCK,
    PACKAGE_LOCK_JSON_V1,
    PACKAGE_LOCK_JSON_V3,
    PNPM_LOCK_YAML,
    UV_LOCK,
)


class TestLockfileParsers:
    def test_find_lockfile_uv(self, tmp_path: Path) -> None:
        (tmp_path / "uv.lock").write_text(UV_LOCK)
        assert _find_lockfile(tmp_path) == tmp_path / "uv.lock"

    def test_find_lockfile_none(self, tmp_path: Path) -> None:
        assert _find_lockfile(tmp_path) is None

    def test_find_lockfile_direct(self, tmp_path: Path) -> None:
        """T-0221: `frob vet uv.lock` passes the lockfile itself as `root`;
        it must resolve directly, not be misread as a directory to search
        under (which would look for uv.lock/uv.lock)."""
        lockfile = tmp_path / "uv.lock"
        lockfile.write_text(UV_LOCK)
        assert _find_lockfile(lockfile) == lockfile

    def test_find_lockfile_bad_name(self, tmp_path: Path) -> None:
        """A file path that isn't one of the supported lockfile names is not
        silently accepted just because it exists."""
        path = tmp_path / "yarn.lock"
        path.write_text("{}")
        assert _find_lockfile(path) is None

    def test_parse_uv_lock(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_lockfile.py::_parse_lockfile kind="unit"
        path = tmp_path / "uv.lock"
        path.write_text(UV_LOCK)
        result = _parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="pypi", name="requests", version="2.31.0") in deps
        assert len(deps) == 2

    def test_parse_package_lock_json_v3(self, tmp_path: Path) -> None:
        path = tmp_path / "package-lock.json"
        path.write_text(PACKAGE_LOCK_JSON_V3)
        result = _parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="lodash", version="4.17.21") in deps
        assert Dependency(ecosystem="npm", name="chalk", version="5.3.0") in deps

    def test_parse_package_lock_json_v1(self, tmp_path: Path) -> None:
        path = tmp_path / "package-lock.json"
        path.write_text(PACKAGE_LOCK_JSON_V1)
        result = _parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="express", version="4.18.2") in deps

    def test_parse_pnpm_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "pnpm-lock.yaml"
        path.write_text(PNPM_LOCK_YAML)
        result = _parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="lodash", version="4.17.21") in deps

    def test_parse_cargo_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "Cargo.lock"
        path.write_text(CARGO_LOCK)
        result = _parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="cargo", name="serde", version="1.0.195") in deps

    def test_unsupported_lockfile(self, tmp_path: Path) -> None:
        path = tmp_path / "yarn.lock"
        result = _parse_lockfile(path)
        assert result.is_err

    def test_malformed_uv_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "uv.lock"
        path.write_text("not valid = [ toml")
        result = _parse_lockfile(path)
        assert result.is_err

    def test_find_all_lockfiles_polyglot_repo(self, tmp_path: Path) -> None:
        # T-0400 audit finding #2: a repo with BOTH a uv.lock and a
        # package-lock.json must have both discovered -- the old
        # `_find_lockfile` returning only the first left every npm
        # dependency completely unscanned.
        # frob:tests src/frob/vet/_lockfile.py::_find_all_lockfiles kind="unit"
        from frob.vet._lockfile import _find_all_lockfiles

        (tmp_path / "uv.lock").write_text(UV_LOCK)
        (tmp_path / "package-lock.json").write_text(PACKAGE_LOCK_JSON_V3)
        found = _find_all_lockfiles(tmp_path)
        assert found == (tmp_path / "uv.lock", tmp_path / "package-lock.json")

    def test_find_all_lockfiles_single(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_lockfile.py::_find_all_lockfiles kind="unit"
        from frob.vet._lockfile import _find_all_lockfiles

        (tmp_path / "uv.lock").write_text(UV_LOCK)
        assert _find_all_lockfiles(tmp_path) == (tmp_path / "uv.lock",)

    def test_find_all_lockfiles_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_lockfile.py::_find_all_lockfiles kind="unit"
        from frob.vet._lockfile import _find_all_lockfiles

        assert _find_all_lockfiles(tmp_path) == ()

    def test_find_all_lockfiles_direct_path(self, tmp_path: Path) -> None:
        # T-0221 parity: a direct lockfile path resolves to a 1-tuple of
        # itself, not a directory search.
        # frob:tests src/frob/vet/_lockfile.py::_find_all_lockfiles kind="unit"
        from frob.vet._lockfile import _find_all_lockfiles

        lockfile = tmp_path / "uv.lock"
        lockfile.write_text(UV_LOCK)
        assert _find_all_lockfiles(lockfile) == (lockfile,)


class TestAllowConfig:
    def test_no_frob_toml_is_advisory_only(self, tmp_path: Path) -> None:
        cfg = _load_vet_config(tmp_path)
        assert cfg.present is False

    def test_no_vet_section_is_advisory_only(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text("check_base = 'main'\n")
        cfg = _load_vet_config(tmp_path)
        assert cfg.present is False

    def test_vet_section_present(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_allow.py::_load_vet_config kind="unit"
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
        cfg = _load_vet_config(tmp_path)
        assert cfg.present is True
        assert cfg.enforce is True
        assert cfg.quarantine_days == 7
        assert cfg.allow["requests"] is True
        assert cfg.allow["jinja2"] == ("sandboxed template compilation, reviewed",)

    def test_wrong_typed_scalars_fall_back_to_defaults(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_allow.py::_load_vet_config kind="unit"
        # A malformed `[vet]` scalar (wrong TOML type) must degrade to the
        # field default, never crash the whole `frob` invocation.
        (tmp_path / "frob.toml").write_text(
            """
[vet]
quarantine_days = ["not", "an", "int"]
registry_base_url = 42
"""
        )
        cfg = _load_vet_config(tmp_path)
        assert cfg.present is True
        assert cfg.quarantine_days == 14
        assert cfg.registry_base_url is None


class TestQuarantine:
    def test_fresh_package_blocked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_hook.py::check_package kind="unit"
        # T-3715: a present [vet] table (declared posture) is required for
        # the age gate to actually block -- see
        # TestAdvisoryHookDoesNotBlock for the no-[vet]-table case.
        import frob.vet._hook as _hook_mod

        (tmp_path / "frob.toml").write_text("[vet]\n")

        def fake_fetch(
            ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0
        ):
            return _RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=2),
                resolved_version=version,
            )

        monkeypatch.setattr(_hook_mod, "_fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "some-new-pkg", "1.0.0", root=tmp_path)
        assert verdict.verdict == "quarantine"
        assert verdict.blocked is True

    def test_old_package_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.vet._hook as _hook_mod

        def fake_fetch(
            ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0
        ):
            return _RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=900),
                resolved_version=version,
            )

        monkeypatch.setattr(_hook_mod, "_fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "requests", "2.31.0", root=tmp_path)
        assert verdict.verdict == "ok"
        assert verdict.blocked is False

    def test_network_failure_degrades_to_unverified(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.vet._hook as _hook_mod

        def fake_fetch(
            ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0
        ):
            return _RegistryResult(
                ok=False, note="could not verify publish date: timeout"
            )

        monkeypatch.setattr(_hook_mod, "_fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "requests", "2.31.0", root=tmp_path)
        assert verdict.verdict == "unverified"
        assert verdict.blocked is False

    def test_typosquat_name_blocked_before_any_registry_lookup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_hook.py::check_package kind="unit"
        # T-1294: pins the typosquat branch of check_package -- a name one
        # edit-distance from a popular pypi package must be blocked as
        # "typosquat" WITHOUT ever reaching the registry publish-date
        # lookup (proven here by making that lookup explode if called).
        import frob.vet._hook as _hook_mod

        def fail_if_called(*args, **kwargs):
            raise AssertionError(
                "registry lookup must not run once a typosquat is found"
            )

        monkeypatch.setattr(_hook_mod, "_fetch_publish_date", fail_if_called)
        verdict = check_package("pypi", "reqeusts", "1.0.0", root=tmp_path)
        assert verdict.verdict == "typosquat"
        assert verdict.blocked is True
        assert "requests" in verdict.message


class TestVetAllowNotAgeBlocked:
    """T-3715: apollo FROBLEMS.md 2026-09-03, confirmed in source -- the age
    gate's own block message says 'add to [vet.allow] after review', but
    `_age_based_verdict` never read `cfg.allow` back. A package listed in
    `[vet.allow]` must not be blocked by the age gate."""

    def test_allow_listed_package_not_age_blocked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_hook.py::check_package kind="unit"
        import frob.vet._hook as _hook_mod

        (tmp_path / "frob.toml").write_text(
            '[vet]\n[vet.allow]\n"some-new-pkg" = true\n'
        )

        def fake_fetch(
            ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0
        ):
            return _RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=2),
                resolved_version=version,
            )

        monkeypatch.setattr(_hook_mod, "_fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "some-new-pkg", "1.0.0", root=tmp_path)
        assert verdict.verdict == "ok"
        assert verdict.blocked is False
        assert "vet.allow" in verdict.message

    def test_allow_listed_with_reasons_not_age_blocked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_hook.py::check_package kind="unit"
        import frob.vet._hook as _hook_mod

        (tmp_path / "frob.toml").write_text(
            '[vet]\n[vet.allow]\n"some-new-pkg" = ["reviewed by ops"]\n'
        )

        def fake_fetch(
            ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0
        ):
            return _RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=2),
                resolved_version=version,
            )

        monkeypatch.setattr(_hook_mod, "_fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "some-new-pkg", "1.0.0", root=tmp_path)
        assert verdict.blocked is False


class TestAdvisoryHookDoesNotBlock:
    """T-3715: apollo FROBLEMS.md 2026-09-03 -- the hook printed
    'advisory-only mode' (no [vet] table in frob.toml) but still blocked
    and exited 2. Advisory mode must warn, never block."""

    def test_no_vet_table_not_age_blocked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_hook.py::check_package kind="unit"
        import frob.vet._hook as _hook_mod

        # no frob.toml at all -> _load_vet_config returns present=False
        def fake_fetch(
            ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0
        ):
            return _RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=2),
                resolved_version=version,
            )

        monkeypatch.setattr(_hook_mod, "_fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "some-new-pkg", "1.0.0", root=tmp_path)
        assert verdict.verdict == "advisory"
        assert verdict.blocked is False

    def test_frob_toml_without_vet_section_not_age_blocked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_hook.py::check_package kind="unit"
        import frob.vet._hook as _hook_mod

        (tmp_path / "frob.toml").write_text("[tool.other]\n")

        def fake_fetch(
            ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0
        ):
            return _RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=2),
                resolved_version=version,
            )

        monkeypatch.setattr(_hook_mod, "_fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "some-new-pkg", "1.0.0", root=tmp_path)
        assert verdict.verdict == "advisory"
        assert verdict.blocked is False


class TestTyposquat:
    def test_damerau_levenshtein_basic(self) -> None:
        assert _damerau_levenshtein("requests", "requests") == 0
        assert _damerau_levenshtein("requets", "requests") == 1
        assert _damerau_levenshtein("laodash", "lodash") == 1

    def test_requets_flags_requests(self) -> None:
        # frob:tests src/frob/vet/_typosquat.py::_find_typosquat kind="unit"
        assert _find_typosquat("pypi", "requets") == "requests"

    def test_laodash_flags_lodash(self) -> None:
        assert _find_typosquat("npm", "laodash") == "lodash"

    def test_known_popular_package_not_flagged(self) -> None:
        assert _find_typosquat("pypi", "requests") is None

    def test_unrelated_name_not_flagged(self) -> None:
        assert _find_typosquat("pypi", "some-totally-unrelated-package-xyz") is None
