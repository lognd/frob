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
    def test_is_available_reflects_path_lookup(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_is_available kind="unit"
        from frob.vet import _osv

        monkeypatch.setattr(
            _osv.shutil, "which", lambda _binary: "/usr/bin/osv-scanner"
        )
        assert _osv._is_available() is True

        monkeypatch.setattr(_osv.shutil, "which", lambda _binary: None)
        assert _osv._is_available() is False

    def test_run_osv_scan_none_when_binary_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scan kind="unit"
        from frob.vet import _osv

        monkeypatch.setattr(_osv.shutil, "which", lambda _binary: None)
        lockfile = tmp_path / "uv.lock"
        lockfile.write_text("version = 1\n")
        assert _osv._run_osv_scan(lockfile) is None

    def test_run_osv_scan_flattens_advisories_from_scanner_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scan kind="unit"
        # T-1294: pins the real JSON-flattening behavior -- one advisory
        # per (package, vulnerability), fixed_version pulled from the LAST
        # "fixed" event across all ranges, aliases carried through.
        from frob.vet import _osv

        monkeypatch.setattr(
            _osv.shutil, "which", lambda _binary: "/usr/bin/osv-scanner"
        )
        payload = json.dumps(
            {
                "results": [
                    {
                        "packages": [
                            {
                                "package": {"name": "requests", "version": "2.0.0"},
                                "vulnerabilities": [
                                    {
                                        "id": "GHSA-xxxx",
                                        "aliases": ["CVE-2023-1234"],
                                        "affected": [
                                            {
                                                "ranges": [
                                                    {
                                                        "events": [
                                                            {"introduced": "0"},
                                                            {"fixed": "2.1.0"},
                                                        ]
                                                    },
                                                    {
                                                        "events": [
                                                            {"fixed": "2.2.0"},
                                                        ]
                                                    },
                                                ]
                                            }
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        )
        monkeypatch.setattr(_osv, "_run_osv_scanner", lambda _lockfile: payload)
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")

        advisories = _osv._run_osv_scan(lockfile)

        assert advisories is not None
        assert len(advisories) == 1
        advisory = advisories[0]
        assert advisory.advisory_id == "GHSA-xxxx"
        assert advisory.package == "requests"
        assert advisory.version == "2.0.0"
        # The LAST-declared "fixed" event across all ranges wins.
        assert advisory.fixed_version == "2.2.0"
        assert advisory.aliases == ("CVE-2023-1234",)
        # cve_ids surfaces the CVE-shaped alias even though the advisory's
        # own id is a GHSA id -- proves the two adapters compose correctly.
        assert _osv.cve_ids(advisory) == ("CVE-2023-1234",)

    def test_run_osv_scan_empty_stdout_is_a_clean_no_findings_result(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scan kind="unit"
        # Empty (whitespace-only) stdout is a real "no vulnerabilities"
        # result, distinct from the None-on-failure sentinel.
        from frob.vet import _osv

        monkeypatch.setattr(
            _osv.shutil, "which", lambda _binary: "/usr/bin/osv-scanner"
        )
        monkeypatch.setattr(_osv, "_run_osv_scanner", lambda _lockfile: "   \n")
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")

        assert _osv._run_osv_scan(lockfile) == ()

    def test_run_osv_scan_unparseable_json_is_none_not_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scan kind="unit"
        # A parse failure must degrade to None (adapter-failed), never to
        # the empty tuple ("scanned clean") -- conflating the two would
        # silently hide a broken adapter as "nothing found" (T-1294: the
        # dangerous-regression class this ticket calls out for vet).
        from frob.vet import _osv

        monkeypatch.setattr(
            _osv.shutil, "which", lambda _binary: "/usr/bin/osv-scanner"
        )
        monkeypatch.setattr(_osv, "_run_osv_scanner", lambda _lockfile: "{not json")
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")

        assert _osv._run_osv_scan(lockfile) is None

    def test_run_osv_scanner_reports_spawn_failure_as_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scanner kind="unit"
        from typani import Err

        from frob.vet import _osv

        monkeypatch.setattr(
            _osv, "run_argv", lambda argv, timeout_s=60.0: Err("spawn failed")
        )
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")
        assert _osv._run_osv_scanner(lockfile) is None

    def test_run_osv_scanner_crash_with_no_output_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scanner kind="unit"
        from typani import Ok

        from frob.gitio import ProcResult
        from frob.vet import _osv

        def fake_run_argv(argv, timeout_s=60.0):
            return Ok(ProcResult(argv=argv, returncode=1, stdout="", stderr="boom"))

        monkeypatch.setattr(_osv, "run_argv", fake_run_argv)
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")
        assert _osv._run_osv_scanner(lockfile) is None

    def test_run_osv_scanner_nonzero_with_output_is_findings_not_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scanner kind="unit"
        # osv-scanner exits non-zero WHEN IT FINDS VULNERABILITIES -- that
        # must be treated as real findings, never conflated with a crash.
        from typani import Ok

        from frob.gitio import ProcResult
        from frob.vet import _osv

        def fake_run_argv(argv, timeout_s=60.0):
            return Ok(
                ProcResult(argv=argv, returncode=1, stdout='{"results": []}', stderr="")
            )

        monkeypatch.setattr(_osv, "run_argv", fake_run_argv)
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")
        assert _osv._run_osv_scanner(lockfile) == '{"results": []}'


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
