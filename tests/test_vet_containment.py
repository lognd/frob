"""Tests for the T-0110 CVE->CWE containment join (docs/strata/threat.md
"CVE: threat intelligence joined to the proof").

Network is MOCKED throughout -- `_nvd.fetch_cwe_for_cve` is monkeypatched
or exercised purely against a pre-seeded `.frob/vet.db` cache, mirroring
`test_vet.py::TestQuarantine`'s `_registry._fetch_publish_date` monkeypatch
idiom. No test in this file makes a real network call.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from frob.strata import (
    Boundary,
    BoundaryDirection,
    Claim,
    Flow,
    KernelModel,
    Node,
    NoFlow,
    Rung,
    bind_code,
)
from frob.vet import _nvd
from frob.vet._cache import ttl_cache_set
from frob.vet._containment import (
    CONTAINED,
    LIVE,
    UNMODELED,
    UNVERIFIED,
    ContainmentFinding,
    build_containment_report,
    find_importing_nodes,
    render_containment_report,
)
from frob.vet._nvd import fetch_cwe_for_cve
from frob.vet._osv import OsvAdvisory, cve_ids


class TestCveIds:
    """`_osv.py::cve_ids` -- CVE-shaped id extraction from advisory + aliases."""

    # frob:tests src/frob/vet/_osv.py::cve_ids kind="unit"
    def test_cve_advisory_id_is_its_own_cve_id(self) -> None:
        advisory = OsvAdvisory("CVE-2024-1234", "pkg", "1.0.0", None)
        assert cve_ids(advisory) == ("CVE-2024-1234",)

    def test_ghsa_advisory_with_cve_alias_resolves(self) -> None:
        advisory = OsvAdvisory(
            "GHSA-xxxx-yyyy-zzzz",
            "pkg",
            "1.0.0",
            None,
            aliases=("CVE-2024-5678", "GHSA-other"),
        )
        assert cve_ids(advisory) == ("CVE-2024-5678",)

    def test_ghsa_advisory_with_no_cve_alias_is_honestly_empty(self) -> None:
        advisory = OsvAdvisory("GHSA-xxxx-yyyy-zzzz", "pkg", "1.0.0", None)
        assert cve_ids(advisory) == ()

    def test_dedupes_repeated_cve_ids(self) -> None:
        advisory = OsvAdvisory(
            "CVE-2024-1234", "pkg", "1.0.0", None, aliases=("CVE-2024-1234",)
        )
        assert cve_ids(advisory) == ("CVE-2024-1234",)


class TestFetchCweForCve:
    """`_nvd.py::fetch_cwe_for_cve` -- offline-first degrade (docs/modules/vet.md VET011)."""

    # frob:tests src/frob/vet/_nvd.py::fetch_cwe_for_cve kind="unit"
    def test_fetch_false_with_no_cache_degrades_loudly(self, tmp_path: Path) -> None:
        result = fetch_cwe_for_cve(
            "CVE-2024-0001", cache_path=tmp_path / "vet.db", fetch=False
        )
        assert result.ok is False
        assert result.cwe_ids == ()
        assert result.note

    def test_network_failure_degrades_loudly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_urlopen(*args, **kwargs):
            raise OSError("network unreachable")

        monkeypatch.setattr(_nvd.urllib.request, "urlopen", fake_urlopen)
        result = fetch_cwe_for_cve(
            "CVE-2024-0002", cache_path=tmp_path / "vet.db", fetch=True
        )
        assert result.ok is False
        assert "could not verify" in result.note

    def test_cached_body_parses_cwe_ids(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "vet.db"
        body = (
            '{"vulnerabilities": [{"cve": {"weaknesses": [{"description": '
            '[{"lang": "en", "value": "CWE-89"}]}]}}]}'
        )
        ttl_cache_set(cache_path, "nvd_cache", _nvd._cache_key("CVE-2024-0003"), body)
        result = fetch_cwe_for_cve("CVE-2024-0003", cache_path=cache_path, fetch=False)
        assert result.ok is True
        assert result.cwe_ids == ("CWE-89",)

    def test_nvd_placeholder_cwe_is_dropped(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "vet.db"
        body = (
            '{"vulnerabilities": [{"cve": {"weaknesses": [{"description": '
            '[{"lang": "en", "value": "NVD-CWE-Other"}]}]}}]}'
        )
        ttl_cache_set(cache_path, "nvd_cache", _nvd._cache_key("CVE-2024-0004"), body)
        result = fetch_cwe_for_cve("CVE-2024-0004", cache_path=cache_path, fetch=False)
        assert result.ok is True
        assert result.cwe_ids == ()

    def test_network_success_populates_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        body = (
            '{"vulnerabilities": [{"cve": {"weaknesses": [{"description": '
            '[{"lang": "en", "value": "CWE-79"}]}]}}]}'
        ).encode()

        class _FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return body

        monkeypatch.setattr(_nvd.urllib.request, "urlopen", lambda *a, **k: _FakeResp())
        cache_path = tmp_path / "vet.db"
        result = fetch_cwe_for_cve("CVE-2024-0005", cache_path=cache_path, fetch=True)
        assert result.ok is True
        assert result.cwe_ids == ("CWE-79",)
        # second call must not need the network (monkeypatch removed).
        monkeypatch.setattr(_nvd.urllib.request, "urlopen", None)
        second = fetch_cwe_for_cve("CVE-2024-0005", cache_path=cache_path, fetch=True)
        assert second.ok is True
        assert second.cwe_ids == ("CWE-79",)

    def test_malformed_cached_body_degrades_without_raising(
        self, tmp_path: Path
    ) -> None:
        """A corrupt/truncated JSON body in the cache must degrade to
        `ok=False` through `_result_from_body`'s parse path -- never raise,
        never silently read as `cwe_ids=()`."""
        cache_path = tmp_path / "vet.db"
        truncated = '{"vulnerabilities": [{"cve": {"weaknesses": [{"desc'
        ttl_cache_set(
            cache_path, "nvd_cache", _nvd._cache_key("CVE-2024-0006"), truncated
        )
        result = fetch_cwe_for_cve("CVE-2024-0006", cache_path=cache_path, fetch=False)
        assert result.ok is False
        assert result.cwe_ids == ()
        assert "could not verify" in result.note

    def test_expired_cache_entry_triggers_a_fresh_fetch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An entry older than `_CACHE_TTL_S` is treated as a miss -- the
        stale mapping must not be served, and a real (mocked) fetch must
        run instead."""
        cache_path = tmp_path / "vet.db"
        stale_body = (
            '{"vulnerabilities": [{"cve": {"weaknesses": [{"description": '
            '[{"lang": "en", "value": "CWE-79"}]}]}}]}'
        )
        ttl_cache_set(
            cache_path, "nvd_cache", _nvd._cache_key("CVE-2024-0007"), stale_body
        )
        # Back-date the just-written row past the TTL.
        conn = sqlite3.connect(str(cache_path))
        try:
            conn.execute(
                "UPDATE nvd_cache SET fetched_at = ? WHERE key = ?",
                (time.time() - _nvd._CACHE_TTL_S - 1, "nvd:CVE-2024-0007"),
            )
            conn.commit()
        finally:
            conn.close()

        fresh_body = (
            '{"vulnerabilities": [{"cve": {"weaknesses": [{"description": '
            '[{"lang": "en", "value": "CWE-89"}]}]}}]}'
        ).encode()

        class _FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return fresh_body

        fetched = {"called": False}

        def fake_urlopen(*args, **kwargs):
            fetched["called"] = True
            return _FakeResp()

        monkeypatch.setattr(_nvd.urllib.request, "urlopen", fake_urlopen)
        result = fetch_cwe_for_cve("CVE-2024-0007", cache_path=cache_path, fetch=True)
        assert fetched["called"] is True
        assert result.ok is True
        assert result.cwe_ids == ("CWE-89",)


class TestFindImportingNodes:
    """`_containment.py::find_importing_nodes` -- code-binding join over the
    dependent import surface."""

    # frob:tests src/frob/vet/_containment.py::find_importing_nodes kind="unit"
    def test_finds_node_importing_the_package(self, tmp_path: Path) -> None:
        (tmp_path / "web.py").write_text("import jinja2\n")
        node = Node(id="Web", trust="trusted", attrs=("code=web.py",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok
        assert find_importing_nodes(binding, tmp_path, "jinja2") == frozenset({"Web"})

    def test_no_node_imports_the_package(self, tmp_path: Path) -> None:
        (tmp_path / "web.py").write_text("import os\n")
        node = Node(id="Web", trust="trusted", attrs=("code=web.py",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok
        assert find_importing_nodes(binding, tmp_path, "jinja2") == frozenset()

    def test_dash_normalized_dist_name_resolves_to_underscore_module(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "web.py").write_text("import foo_bar\n")
        node = Node(id="Web", trust="trusted", attrs=("code=web.py",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok
        assert find_importing_nodes(binding, tmp_path, "foo-bar") == frozenset({"Web"})


class TestBuildContainmentReport:
    """`_containment.py::build_containment_report` -- the CVE/CWE/discharge join."""

    def _model_with_discharged_sql(self) -> KernelModel:
        node = Node(id="Api", trust="trusted", may=("sql",), attrs=("code=api.py",))
        evil = Node(id="Evil", trust="foreign")
        return KernelModel(
            nodes=(node, evil),
            flows=(Flow(id="f1", src="Evil", dst="Api"),),
            boundaries=(
                Boundary(
                    id="b1",
                    flow_id="f1",
                    direction=BoundaryDirection.ENDORSE,
                    from_level="foreign",
                    to_level="trusted",
                    predicate="parameterization",
                    # G1 (docs/audits/strata.md): an ENDORSE boundary must
                    # carry an evidence ref resolving to a real claim to
                    # count as a chokepoint mitigation of the correct kind.
                    obligations=("weakness:CWE-89:Api",),
                ),
            ),
            claims=(
                Claim(
                    id="weakness:CWE-89:Api",
                    body=NoFlow(src="foreign", dst="Api"),
                    required_rung=Rung.L4,
                ),
            ),
        )

    def _model_with_undischarged_sql(self) -> KernelModel:
        node = Node(id="Api", trust="trusted", may=("sql",), attrs=("code=api.py",))
        return KernelModel(nodes=(node,))

    # frob:tests src/frob/vet/_containment.py::build_containment_report kind="unit"
    def test_live_finding_when_obligation_undischarged(self, tmp_path: Path) -> None:
        (tmp_path / "api.py").write_text("import psycopg2\n")
        model = self._model_with_undischarged_sql()
        binding = bind_code(model, tmp_path).danger_ok

        advisory = OsvAdvisory("CVE-2024-9001", "psycopg2", "2.9.0", "2.9.1")
        cache_path = tmp_path / "vet.db"
        body = (
            '{"vulnerabilities": [{"cve": {"weaknesses": [{"description": '
            '[{"lang": "en", "value": "CWE-89"}]}]}}]}'
        )
        ttl_cache_set(cache_path, "nvd_cache", _nvd._cache_key("CVE-2024-9001"), body)

        report = build_containment_report(
            (advisory,), model, binding, tmp_path, cache_path=cache_path, fetch=False
        )
        assert len(report.findings) == 1
        finding = report.findings[0]
        assert finding.state == LIVE
        assert finding.node_id == "Api"
        assert finding.cwe_ids == ("CWE-89",)

    def test_contained_finding_when_obligation_discharged(self, tmp_path: Path) -> None:
        # T-0630: G1's code-bound-predicate join is now wired all the way
        # through `build_containment_report`, so a genuine CONTAINED
        # finding needs `parameterization` actually CALLED in Api's own
        # bound code, not merely resolved to an in-model claim (T-0498's
        # weaker half alone is no longer sufficient once a real `binding`/
        # `root` is supplied, matching `test_threat.py::
        # TestCodeBoundMitigationPredicate`'s positive case).
        (tmp_path / "api.py").write_text(
            "import psycopg2\n\n\ndef query(cur, q, args):\n"
            "    return parameterization(cur, q, args)\n"
        )
        model = self._model_with_discharged_sql()
        binding = bind_code(model, tmp_path).danger_ok

        advisory = OsvAdvisory("CVE-2024-9002", "psycopg2", "2.9.0", "2.9.1")
        cache_path = tmp_path / "vet.db"
        body = (
            '{"vulnerabilities": [{"cve": {"weaknesses": [{"description": '
            '[{"lang": "en", "value": "CWE-89"}]}]}}]}'
        )
        ttl_cache_set(cache_path, "nvd_cache", _nvd._cache_key("CVE-2024-9002"), body)

        report = build_containment_report(
            (advisory,), model, binding, tmp_path, cache_path=cache_path, fetch=False
        )
        assert len(report.findings) == 1
        finding = report.findings[0]
        assert finding.state == CONTAINED
        assert finding.node_id == "Api"

    def test_unmodeled_when_no_node_imports_the_package(self, tmp_path: Path) -> None:
        """Genuine no-coverage (NVD lookup succeeds, nothing binds the
        dependency) is `UNMODELED`, not `UNVERIFIED` -- the two must never
        be conflated in either direction."""
        (tmp_path / "api.py").write_text("import os\n")
        node = Node(id="Api", trust="trusted", may=("sql",), attrs=("code=api.py",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok

        advisory = OsvAdvisory("CVE-2024-9003", "psycopg2", "2.9.0", None)
        cache_path = tmp_path / "vet.db"
        body = (
            '{"vulnerabilities": [{"cve": {"weaknesses": [{"description": '
            '[{"lang": "en", "value": "CWE-89"}]}]}}]}'
        )
        ttl_cache_set(cache_path, "nvd_cache", _nvd._cache_key("CVE-2024-9003"), body)

        report = build_containment_report(
            (advisory,), model, binding, tmp_path, cache_path=cache_path, fetch=False
        )
        assert len(report.findings) == 1
        assert report.findings[0].state == UNMODELED
        assert report.findings[0].node_id is None

    def test_unverified_when_nvd_lookup_fails(self, tmp_path: Path) -> None:
        """A CVE whose NVD lookup could not be completed is `UNVERIFIED`,
        DISTINCT from `UNMODELED` (genuine no-coverage) -- an outage must
        never be reported as if it were a benign no-coverage result."""
        (tmp_path / "api.py").write_text("import psycopg2\n")
        node = Node(id="Api", trust="trusted", may=("sql",), attrs=("code=api.py",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok

        advisory = OsvAdvisory("CVE-2024-9004", "psycopg2", "2.9.0", None)
        cache_path = tmp_path / "vet.db"  # no cache entry, fetch=False -> ok=False

        report = build_containment_report(
            (advisory,), model, binding, tmp_path, cache_path=cache_path, fetch=False
        )
        assert len(report.findings) == 1
        assert report.findings[0].state == UNVERIFIED
        assert report.findings[0].state != UNMODELED

    def test_non_cve_advisory_yields_no_findings(self, tmp_path: Path) -> None:
        (tmp_path / "api.py").write_text("import psycopg2\n")
        node = Node(id="Api", trust="trusted", may=("sql",), attrs=("code=api.py",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok

        advisory = OsvAdvisory("GHSA-no-cve-alias", "psycopg2", "2.9.0", None)
        report = build_containment_report(
            (advisory,),
            model,
            binding,
            tmp_path,
            cache_path=tmp_path / "vet.db",
            fetch=False,
        )
        assert report.findings == ()


class TestRenderContainmentReport:
    """`_containment.py::render_containment_report` -- text rendering."""

    # frob:tests src/frob/vet/_containment.py::render_containment_report kind="unit"
    def test_empty_report_renders_explicit_note(self) -> None:
        from frob.vet._containment import ContainmentReport

        assert "no CVE findings" in render_containment_report(ContainmentReport())

    def test_live_findings_sort_before_contained(self) -> None:
        from frob.vet._containment import ContainmentReport

        report = ContainmentReport(
            findings=(
                ContainmentFinding(
                    cve_id="CVE-2024-0001",
                    package="a",
                    version="1.0",
                    state=CONTAINED,
                    node_id="A",
                ),
                ContainmentFinding(
                    cve_id="CVE-2024-0002",
                    package="b",
                    version="1.0",
                    state=LIVE,
                    node_id="B",
                ),
            )
        )
        text = render_containment_report(report)
        lines = text.splitlines()
        assert "LIVE" in lines[0]
        assert "contained" in lines[1]

    def test_unverified_sorts_between_live_and_contained(self) -> None:
        """`UNVERIFIED` must render strictly after `LIVE` and strictly
        before both `CONTAINED` and `UNMODELED` -- a triage consumer
        scanning top-to-bottom must hit every unresolved NVD outage before
        anything the join actually resolved (docs/strata/threat.md "CVE:
        threat intelligence joined to the proof")."""
        from frob.vet._containment import ContainmentReport

        report = ContainmentReport(
            findings=(
                ContainmentFinding(
                    cve_id="CVE-2024-0003",
                    package="c",
                    version="1.0",
                    state=UNMODELED,
                ),
                ContainmentFinding(
                    cve_id="CVE-2024-0001",
                    package="a",
                    version="1.0",
                    state=CONTAINED,
                    node_id="A",
                ),
                ContainmentFinding(
                    cve_id="CVE-2024-0004",
                    package="d",
                    version="1.0",
                    state=UNVERIFIED,
                ),
                ContainmentFinding(
                    cve_id="CVE-2024-0002",
                    package="b",
                    version="1.0",
                    state=LIVE,
                    node_id="B",
                ),
            )
        )
        text = render_containment_report(report)
        lines = text.splitlines()
        assert "LIVE" in lines[0]
        assert "UNVERIFIED" in lines[1]
        assert "contained" in lines[2]
        assert "unmodeled" in lines[3]
