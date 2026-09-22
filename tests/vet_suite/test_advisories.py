import json
from pathlib import Path

import pytest


class TestLifecycleScripts:
    def test_finds_postinstall_script(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_lifecycle.py::_scan_lifecycle_scripts kind="unit"
        from frob.vet._lifecycle import _scan_lifecycle_scripts

        pkg_dir = tmp_path / "node_modules" / "sketchy-pkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "package.json").write_text(
            json.dumps(
                {
                    "name": "sketchy-pkg",
                    "scripts": {"postinstall": "node evil.js"},
                }
            )
        )
        found = _scan_lifecycle_scripts(tmp_path)
        assert found == {"sketchy-pkg": ("postinstall",)}

    def test_no_node_modules_returns_empty(self, tmp_path: Path) -> None:
        from frob.vet._lifecycle import _scan_lifecycle_scripts

        assert _scan_lifecycle_scripts(tmp_path) == {}


class TestOsvAdapter:
    """T-5138: OSV.dev in-process HTTP advisory adapter -- no external
    binary, no network hit in these tests (urlopen is monkeypatched)."""

    def test_query_advisories_positive_control_fires_a_known_advisory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::query_advisories kind="unit"
        # Positive control: a fixture dependency + a planted OSV response
        # must yield a real advisory -- proves the client is actually wired
        # up, not just silently passing on every input.
        from frob.vet import _osv
        from frob.vet._models import Dependency

        dep = Dependency(ecosystem="pypi", name="requests", version="2.31.0")

        def fake_post(url, _body, _timeout_s):
            assert url == _osv._QUERYBATCH_URL
            return json.dumps({"results": [{"vulns": [{"id": "GHSA-xxxx"}]}]})

        def fake_get(url, _timeout_s):
            assert url == _osv._VULN_URL.format(id="GHSA-xxxx")
            return json.dumps(
                {
                    "id": "GHSA-xxxx",
                    "aliases": ["CVE-2023-1234"],
                    "summary": "planted fixture advisory",
                    "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N"}],
                    "affected": [{"ranges": [{"events": [{"fixed": "2.32.0"}]}]}],
                }
            )

        monkeypatch.setattr(_osv, "_http_post_json", fake_post)
        monkeypatch.setattr(_osv, "_http_get_json", fake_get)

        result = _osv.query_advisories(
            (dep,), cache_path=tmp_path / "vet.db", fetch=True
        )
        assert result.is_ok
        advisories = result.danger_ok[dep]
        assert len(advisories) == 1
        advisory = advisories[0]
        assert advisory.advisory_id == "GHSA-xxxx"
        assert advisory.fixed_version == "2.32.0"
        assert advisory.severity == "CVSS:3.1/AV:N"
        assert _osv.cve_ids(advisory) == ("CVE-2023-1234",)

    def test_query_advisories_serves_fresh_cache_with_no_network_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::query_advisories kind="unit"
        from frob.vet import _osv
        from frob.vet._cache import ttl_cache_set
        from frob.vet._models import Dependency

        dep = Dependency(ecosystem="pypi", name="requests", version="2.31.0")
        cache_path = tmp_path / "vet.db"
        ttl_cache_set(
            cache_path,
            _osv._CACHE_TABLE,
            _osv._cache_key("pypi", "requests", "2.31.0"),
            json.dumps(
                [
                    {
                        "advisory_id": "GHSA-cached",
                        "package": "requests",
                        "version": "2.31.0",
                        "fixed_version": "2.32.0",
                        "aliases": [],
                        "severity": None,
                        "summary": "",
                    }
                ]
            ),
        )

        def _no_connect(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("fresh cache must never reach the network")

        monkeypatch.setattr(_osv, "_http_post_json", _no_connect)
        monkeypatch.setattr(_osv, "_http_get_json", _no_connect)

        result = _osv.query_advisories((dep,), cache_path=cache_path, fetch=True)
        assert result.is_ok
        assert result.danger_ok[dep][0].advisory_id == "GHSA-cached"

    def test_query_advisories_no_cache_no_network_is_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::query_advisories kind="unit"
        # VET012's premise: cold cache + unreachable network must be an
        # honest Err, never a silent "no advisories" Ok.
        from frob.vet import _osv
        from frob.vet._models import Dependency

        dep = Dependency(ecosystem="pypi", name="requests", version="2.31.0")
        monkeypatch.setattr(_osv, "_http_post_json", lambda *a, **kw: None)

        result = _osv.query_advisories(
            (dep,), cache_path=tmp_path / "vet.db", fetch=True
        )
        assert result.is_err
        assert result.danger_err == _osv.OsvQueryError.Unavailable

    def test_query_advisories_stale_cache_beyond_max_age_is_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::query_advisories kind="unit"
        import time

        from frob.vet import _osv
        from frob.vet._cache import ttl_cache_set
        from frob.vet._models import Dependency

        dep = Dependency(ecosystem="pypi", name="requests", version="2.31.0")
        cache_path = tmp_path / "vet.db"
        ttl_cache_set(
            cache_path,
            _osv._CACHE_TABLE,
            _osv._cache_key("pypi", "requests", "2.31.0"),
            json.dumps([]),
        )
        # Back-date the entry well past the default 7d max age.
        import sqlite3

        conn = sqlite3.connect(str(cache_path))
        conn.execute(
            f"UPDATE {_osv._CACHE_TABLE} SET fetched_at = ?",  # noqa: S608
            (time.time() - 30 * 86400,),
        )
        conn.commit()
        conn.close()

        monkeypatch.setattr(_osv, "_http_post_json", lambda *a, **kw: None)

        result = _osv.query_advisories(
            (dep,), cache_path=cache_path, fetch=True, max_age_days=7.0
        )
        assert result.is_err
        assert result.danger_err == _osv.OsvQueryError.Unavailable

    def test_query_advisories_net_disabled_falls_back_to_stale_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::query_advisories kind="unit"
        # T-0822: FROB_DISABLE_NET degrades exactly like a network failure
        # -- serving a still-usable (within max_age_days) stale cache
        # entry, never crashing and never calling urlopen.
        import time

        from frob.vet import _osv
        from frob.vet._cache import ttl_cache_set
        from frob.vet._models import Dependency

        dep = Dependency(ecosystem="pypi", name="requests", version="2.31.0")
        cache_path = tmp_path / "vet.db"
        ttl_cache_set(
            cache_path,
            _osv._CACHE_TABLE,
            _osv._cache_key("pypi", "requests", "2.31.0"),
            json.dumps([]),
        )
        import sqlite3

        conn = sqlite3.connect(str(cache_path))
        conn.execute(
            f"UPDATE {_osv._CACHE_TABLE} SET fetched_at = ?",  # noqa: S608
            (time.time() - 2 * 86400,),
        )
        conn.commit()
        conn.close()

        monkeypatch.setenv("FROB_DISABLE_NET", "1")

        def _no_connect(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("net-disabled path must never reach the network")

        monkeypatch.setattr(_osv, "_http_post_json", _no_connect)

        result = _osv.query_advisories(
            (dep,), cache_path=cache_path, fetch=True, max_age_days=7.0
        )
        assert result.is_ok
        assert result.danger_ok[dep] == ()

    def test_query_advisories_unmapped_ecosystem_is_a_clean_skip(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::query_advisories kind="unit"
        # A dependency in an ecosystem OSV has no data for is honestly
        # reported as "no advisories", not a network failure.
        from frob.vet import _osv
        from frob.vet._models import Dependency

        dep = Dependency(ecosystem="nuget", name="Newtonsoft.Json", version="1.0.0")
        result = _osv.query_advisories((dep,), cache_path=tmp_path / "vet.db")
        assert result.is_ok
        assert result.danger_ok[dep] == ()


class TestVetConfigDefault:
    def test_default_frob_toml_enables_advisories_with_no_opt_in(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_allow.py::_load_vet_config kind="unit"
        # T-5138 acceptance [4]: a fresh clone's default `[vet]` table (no
        # `advisories`/`osv` key at all) must run the advisory query with no
        # opt-in flag -- the query executes automatically, on by default.
        from frob.vet._allow import _load_vet_config

        (tmp_path / "frob.toml").write_text("[vet]\nenforce = true\n")
        cfg = _load_vet_config(tmp_path)
        assert cfg.advisories is True
        assert cfg.advisory_max_age_days == 7.0

    def test_deprecated_osv_key_still_disables_advisories(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_allow.py::_load_vet_config kind="unit"
        from frob.vet._allow import _load_vet_config

        (tmp_path / "frob.toml").write_text("[vet]\nosv = false\n")
        cfg = _load_vet_config(tmp_path)
        assert cfg.advisories is False


class TestRegistryLookup:
    def test_fetch_publish_date_degrades_on_network_failure(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_registry.py::_fetch_publish_date kind="unit"
        from frob.vet._registry import _fetch_publish_date

        result = _fetch_publish_date(
            "pypi",
            "some-package-that-should-not-resolve",
            "1.0.0",
            cache_path=tmp_path / "vet.db",
            base_url="http://127.0.0.1:1",
            timeout_s=0.5,
        )
        assert result.ok is False
        assert result.published_at is None

    # frob:ticket T-0822
    def test_fetch_publish_date_refuses_when_net_disabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0822: `FROB_DISABLE_NET` degrades `_fetch_publish_date` to
        `ok=False` without ever calling `urlopen` -- a no-connect spy
        proves the kill switch short-circuits before the socket opens."""
        # frob:tests src/frob/vet/_registry.py::_fetch_publish_date kind="unit"
        # frob:tests src/frob/vet/_registry.py::_result_from_network kind="unit"
        from frob.vet import _registry

        monkeypatch.setenv("FROB_DISABLE_NET", "1")

        def _no_connect(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("urlopen must not be called while net is disabled")

        monkeypatch.setattr(_registry.urllib.request, "urlopen", _no_connect)

        result = _registry._fetch_publish_date(
            "pypi",
            "some-package",
            "1.0.0",
            cache_path=tmp_path / "vet.db",
            base_url="http://127.0.0.1:1",
            timeout_s=0.5,
        )
        assert result.ok is False
        assert result.published_at is None
        assert "net disabled" in result.note

    def test_url_for_every_supported_ecosystem_and_version_form(self) -> None:
        # frob:tests src/frob/vet/_registry.py::_url_for kind="unit"
        # T-1294: pins the real per-ecosystem URL shape -- every branch
        # (pypi latest/pinned, npm, cargo, both base_url override and the
        # real-host default) plus the unsupported-ecosystem error.
        from frob.vet._registry import _url_for

        assert _url_for("pypi", "requests", "latest", None) == (
            "https://pypi.org/pypi/requests/json"
        )
        assert _url_for("pypi", "requests", "2.31.0", None) == (
            "https://pypi.org/pypi/requests/2.31.0/json"
        )
        assert _url_for("npm", "lodash", "latest", None) == (
            "https://registry.npmjs.org/lodash"
        )
        assert _url_for("cargo", "serde", "latest", None) == (
            "https://crates.io/api/v1/crates/serde/versions"
        )
        assert _url_for("pypi", "requests", "2.31.0", "http://fake") == (
            "http://fake/pypi/requests/2.31.0/json"
        )
        assert _url_for("npm", "lodash", "latest", "http://fake") == (
            "http://fake/npm/lodash"
        )
        assert _url_for("cargo", "serde", "1.0", "http://fake") == (
            "http://fake/crates/serde/versions"
        )
        with pytest.raises(ValueError, match="unsupported ecosystem"):
            _url_for("rubygems", "rails", "latest", None)

    def test_parse_published_pypi_latest_resolves_current_release(self) -> None:
        # frob:tests src/frob/vet/_registry.py::_parse_published kind="unit"
        from frob.vet._registry import _parse_published

        body = json.dumps(
            {
                "info": {"version": "2.31.0"},
                "releases": {
                    "2.31.0": [{"upload_time_iso_8601": "2023-05-22T00:00:00"}]
                },
            }
        )
        resolved, published = _parse_published("pypi", "requests", "latest", body)
        assert resolved == "2.31.0"
        assert published is not None
        assert published.year == 2023

    def test_parse_published_npm_and_cargo(self) -> None:
        # frob:tests src/frob/vet/_registry.py::_parse_published kind="unit"
        # T-1294: npm and cargo were entirely unexercised before this --
        # a detector that only ever parsed pypi bodies would silently
        # never flag/verify anything for the other two ecosystems.
        from frob.vet._registry import _parse_published

        npm_body = json.dumps(
            {
                "dist-tags": {"latest": "4.17.21"},
                "time": {"4.17.21": "2021-02-20T00:00:00.000Z"},
            }
        )
        resolved, published = _parse_published("npm", "lodash", "latest", npm_body)
        assert resolved == "4.17.21"
        assert published is not None
        assert published.year == 2021

        cargo_body = json.dumps(
            {
                "versions": [
                    {"num": "1.0.130", "created_at": "2022-01-01T00:00:00.000Z"},
                    {"num": "1.0.100", "created_at": "2020-01-01T00:00:00.000Z"},
                ]
            }
        )
        resolved, published = _parse_published("cargo", "serde", "latest", cargo_body)
        assert resolved == "1.0.130"  # first entry = latest
        assert published is not None
        assert published.year == 2022

        resolved, published = _parse_published("cargo", "serde", "1.0.100", cargo_body)
        assert resolved == "1.0.100"
        assert published is not None
        assert published.year == 2020

        # A pinned version absent from the registry's version list must
        # degrade to (None, None), never guess a neighboring entry.
        resolved, published = _parse_published("cargo", "serde", "9.9.9", cargo_body)
        assert resolved is None
        assert published is None

    def test_result_from_cached_malformed_body_degrades_to_unverified(self) -> None:
        # frob:tests src/frob/vet/_registry.py::_result_from_cached kind="unit"
        # T-1294: a corrupted cache entry must degrade to ok=False, never
        # crash the caller or silently pass through unparsed data.
        from frob.vet._registry import _result_from_cached

        result = _result_from_cached(
            "pypi", "requests", "2.31.0", "pypi:requests:2.31.0", "{not json"
        )
        assert result.ok is False
        assert "unparseable" in result.note

    def test_fetch_publish_date_reuses_cache_without_any_network_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_registry.py::_fetch_publish_date kind="unit"
        # T-1294: a pinned version already cached must be served straight
        # from the TTL cache -- proven by making urlopen explode if it is
        # ever reached.
        from frob.vet import _registry
        from frob.vet._cache import ttl_cache_set

        cache_path = tmp_path / "vet.db"
        cached_body = json.dumps(
            {"releases": {"2.31.0": [{"upload_time_iso_8601": "2023-05-22T00:00:00"}]}}
        )
        ttl_cache_set(
            cache_path, _registry._CACHE_TABLE, "pypi:requests:2.31.0", cached_body
        )

        def _no_connect(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("cached lookup must never reach the network")

        monkeypatch.setattr(_registry.urllib.request, "urlopen", _no_connect)

        result = _registry._fetch_publish_date(
            "pypi",
            "requests",
            "2.31.0",
            cache_path=cache_path,
            base_url="http://127.0.0.1:1",
        )
        assert result.ok is True
        assert result.resolved_version == "2.31.0"
        assert result.published_at is not None

    def test_result_from_network_unparseable_response_body(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_registry.py::_result_from_network kind="unit"
        # T-1294: a successful fetch that returns a body the parser can't
        # read must degrade to ok=False, distinct from a network failure.
        from frob.vet import _registry

        class _FakeResponse:
            def __enter__(self) -> "_FakeResponse":
                return self

            def __exit__(self, *exc: object) -> bool:
                return False

            def read(self) -> bytes:
                return b"{not json"

        monkeypatch.setattr(
            _registry.urllib.request, "urlopen", lambda *a, **kw: _FakeResponse()
        )
        result = _registry._result_from_network(
            "pypi",
            "requests",
            "2.31.0",
            "pypi:requests:2.31.0",
            "https://pypi.org/pypi/requests/2.31.0/json",
            tmp_path / "vet.db",
            5.0,
        )
        assert result.ok is False
        assert "could not verify publish date" in result.note


class TestNvdLookup:
    # frob:ticket T-0822
    def test_fetch_cwe_for_cve_refuses_when_net_disabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0822: `FROB_DISABLE_NET` degrades `fetch_cwe_for_cve` to
        `ok=False` without ever calling `urlopen` -- a no-connect spy
        proves the kill switch short-circuits before the socket opens."""
        # frob:tests src/frob/vet/_nvd.py::fetch_cwe_for_cve kind="unit"
        # frob:tests src/frob/vet/_nvd.py::_fetch_from_network kind="unit"
        from frob.vet import _nvd

        monkeypatch.setenv("FROB_DISABLE_NET", "1")

        def _no_connect(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("urlopen must not be called while net is disabled")

        monkeypatch.setattr(_nvd.urllib.request, "urlopen", _no_connect)

        result = _nvd.fetch_cwe_for_cve(
            "CVE-2024-00000",
            cache_path=tmp_path / "vet.db",
            base_url="http://127.0.0.1:1",
            timeout_s=0.5,
        )
        assert result.ok is False
        assert result.cwe_ids == ()
        assert "net disabled" in result.note


class TestSourceLocation:
    def test_locate_pypi_source_from_venv(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_source.py::_locate_pypi_source kind="unit"
        from frob.vet._source import _locate_pypi_source

        site_packages = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages"
        pkg_dir = site_packages / "some_pkg"
        pkg_dir.mkdir(parents=True)
        found = _locate_pypi_source(tmp_path, "some-pkg", "1.0.0")
        assert found == pkg_dir

    def test_locate_pypi_source_missing_returns_none(self, tmp_path: Path) -> None:
        from frob.vet._source import _locate_pypi_source

        assert _locate_pypi_source(tmp_path, "totally-absent-pkg", "1.0.0") is None

    def test_locate_npm_source_from_node_modules(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_source.py::_locate_npm_source kind="unit"
        from frob.vet._source import _locate_npm_source

        pkg_dir = tmp_path / "node_modules" / "lodash"
        pkg_dir.mkdir(parents=True)
        assert _locate_npm_source(tmp_path, "lodash") == pkg_dir

    def test_locate_npm_source_missing_returns_none(self, tmp_path: Path) -> None:
        from frob.vet._source import _locate_npm_source

        assert _locate_npm_source(tmp_path, "not-installed") is None

    def test_locate_cargo_source_missing_registry_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_source.py::_locate_cargo_source kind="unit"
        from frob.vet._source import _locate_cargo_source

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert _locate_cargo_source("serde", "1.0.195") is None

    def test_locate_source_dispatches_by_ecosystem(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_source.py::_locate_source kind="unit"
        from frob.vet._source import _locate_source

        pkg_dir = tmp_path / "node_modules" / "lodash"
        pkg_dir.mkdir(parents=True)
        assert _locate_source(tmp_path, "npm", "lodash", "4.17.21") == pkg_dir
        assert _locate_source(tmp_path, "unknown-ecosystem", "x", "1.0.0") is None
