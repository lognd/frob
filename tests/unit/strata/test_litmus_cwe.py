"""Per-CWE litmus fixture coverage (T-0145, docs/strata/threat.md#litmus-
coverage): every `WeaknessEntry` in `CWE_CATALOG` and `CWE_TOP_25_CATALOG`
must be exercised by a real `.strata` litmus project (`tests/unit/strata/
litmus/*.strata`) run through the actual `parse_module -> elaborate ->
check_discharge_completeness` pipeline -- the same round trip design/
litmus/audit_vuln.strata + audit_hardened.strata already prove for
CWE-89/CWE-639 (T-0115/T-0138) -- never a hand-built `KernelModel`
fixture (that precedent stays in test_threat.py's `TestDischarge
Completeness`/`TestCweTop25` classes).

`_FIXTURES` is parametrized over the UNION of both catalogs, keyed by cwe
id (drift-lock, vacuous-pass doctrine: a future `WeaknessEntry` with no
`_FIXTURES` entry fails `test_every_catalog_entry_has_a_fixture_mapping`
below rather than silently passing). Three ids (CWE-22/CWE-352/CWE-798)
are cataloged with `capability_kind=None` and structurally can never fire
under `_fired_obligations`/`_entries_by_capability_kind` -- a design
finding documented in docs/strata/threat.md and asserted explicitly here
as a non-firing fixture, never a skip. T-0345 (2025 CWE Top 25 bump)
added `CWE-639` to the union catalog, reusing `cwe_89_vuln.strata`/
`cwe_89_hardened.strata` (SAME `sql` capability join CWE-89 already fires
on, disclosed reuse not a near-duplicate fixture) -- CWE-200 was
considered but classified `OutOfScopeEntry` instead (matching
docs/design/registry/weaknesses.yaml's independent disposition sweep),
so it needs no litmus fixture at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.strata import KernelModel, elaborate, parse_module
from frob.strata._threat import (
    CWE_CATALOG,
    CWE_TOP_25_CATALOG,
    CWE_TOP_25_OUT_OF_SCOPE,
    CWE_TOP_25_VIEWS,
    check_catalog_completeness,
    check_discharge_completeness,
)


# frob:waive DUP001 reason="parallel litmus scenario fixtures: 7 sites across 7 \
# file(s) sharing the exhaustiveness-fixture arrange-act shape by design (store-backed \
# vs non-store-backed, or per-CWE scenario variants); extracting would obscure \
# per-scenario intent"
def _repo_root() -> Path:
    """Walk up from this file until a directory containing `frob.toml` is found."""
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "frob.toml").is_file():
            return candidate
    raise RuntimeError(
        "could not locate repo root (no frob.toml found above test file)"
    )


_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"

_UNION_CATALOG: tuple = CWE_CATALOG + CWE_TOP_25_CATALOG


def _load_model(filename: str) -> KernelModel:
    """Parse+elaborate one `.strata` fixture under `litmus/` end to end --
    the real `strata_core` parser, never a hand-built `KernelModel`."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


#: cwe id -> (vuln filename, node id) for ids whose `capability_kind` is
#: set (they DO fire); `None` for ids whose `capability_kind` is `None`
#: (they structurally never fire -- the design finding documented in
#: docs/strata/threat.md#litmus-coverage).
_FIRING_FIXTURES: dict[str, tuple[str, str] | None] = {
    "CWE-79": ("cwe_79_vuln.strata", "web"),
    "CWE-89": ("cwe_89_vuln.strata", "db"),
    "CWE-78": ("cwe_exec_vuln.strata", "runner"),
    "CWE-22": None,
    "CWE-918": ("cwe_918_vuln.strata", "fetcher"),
    "CWE-502": ("cwe_502_vuln.strata", "worker"),
    "CWE-922": ("cwe_922_vuln.strata", "app"),
    "CWE-352": None,
    "CWE-798": None,
    "CWE-94": ("cwe_exec_vuln.strata", "runner"),
    "CWE-611": None,
    "CWE-639": ("cwe_89_vuln.strata", "db"),
}

#: cwe id -> (hardened filename, node id) mirroring `_FIRING_FIXTURES` for
#: the ids that fire; absent for the never-fire ids (nothing to discharge).
_HARDENED_FIXTURES: dict[str, tuple[str, str]] = {
    "CWE-79": ("cwe_79_hardened.strata", "web"),
    "CWE-89": ("cwe_89_hardened.strata", "db"),
    "CWE-78": ("cwe_exec_hardened.strata", "runner"),
    "CWE-918": ("cwe_918_hardened.strata", "fetcher"),
    "CWE-502": ("cwe_502_hardened.strata", "worker"),
    "CWE-922": ("cwe_922_hardened.strata", "app"),
    "CWE-94": ("cwe_exec_hardened.strata", "runner"),
    "CWE-639": ("cwe_89_hardened.strata", "db"),
}

#: cwe id -> non-firing fixture filename for the `capability_kind=None`
#: design-finding ids.
_UNFIRED_FIXTURES: dict[str, str] = {
    "CWE-22": "cwe_22_unfired.strata",
    "CWE-352": "cwe_352_unfired.strata",
    "CWE-798": "cwe_798_unfired.strata",
    "CWE-611": "cwe_611_unfired.strata",
}


class TestFixtureCoverageIsExhaustive:
    """Drift-lock: `_FIRING_FIXTURES` must cover EVERY id in the union
    catalog, keyed 1:1 -- a future `WeaknessEntry` added to `CWE_CATALOG`
    or `CWE_TOP_25_CATALOG` with no entry here fails this test, never
    silently skips (T-0145 vacuous-pass doctrine)."""

    # frob:tests src/frob/strata/_threat.py::CWE_CATALOG kind="unit"
    # frob:ticket T-0145
    def test_every_catalog_entry_has_a_fixture_mapping(self):
        catalog_ids = {e.id for e in _UNION_CATALOG}
        assert set(_FIRING_FIXTURES) == catalog_ids

    # frob:tests src/frob/strata/_threat.py::CWE_CATALOG kind="unit"
    # frob:ticket T-0145
    def test_unfired_ids_are_exactly_the_capability_kind_none_entries(self):
        none_ids = {e.id for e in _UNION_CATALOG if e.capability_kind is None}
        assert none_ids == set(_UNFIRED_FIXTURES)
        assert none_ids == {cwe for cwe, v in _FIRING_FIXTURES.items() if v is None}

    # frob:tests src/frob/strata/_threat.py::CWE_CATALOG kind="unit"
    # frob:ticket T-0145
    def test_every_firing_id_also_has_a_hardened_fixture(self):
        firing_ids = {cwe for cwe, v in _FIRING_FIXTURES.items() if v is not None}
        assert firing_ids == set(_HARDENED_FIXTURES)


class TestOutOfScopeExemptionMatchesCatalogExactly:
    """T-0145: the `cwe-top-25` `OutOfScopeEntry` set must be exactly the
    view's members this litmus suite's catalog does NOT cover -- no id
    silently escapes either the fixture table above or the out-of-scope
    list (same THREAT001 exhaustiveness proof test_threat.py's
    `TestCweTop25.test_cwe_top_25_view_is_satisfied` already runs, cited
    here directly against the litmus suite's own catalog union)."""

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    # frob:ticket T-0145
    def test_cwe_top_25_view_is_satisfied_by_the_litmus_catalog(self):
        result = check_catalog_completeness(
            "cwe-top-25",
            catalog=_UNION_CATALOG,
            out_of_scope=CWE_TOP_25_OUT_OF_SCOPE,
            views=CWE_TOP_25_VIEWS,
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE kind="unit"
    # frob:ticket T-0145
    def test_out_of_scope_ids_are_disjoint_from_the_fixture_catalog(self):
        catalog_ids = {e.id for e in _UNION_CATALOG}
        out_of_scope_ids = {e.id for e in CWE_TOP_25_OUT_OF_SCOPE}
        assert catalog_ids.isdisjoint(out_of_scope_ids)

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE kind="unit"
    # frob:ticket T-0145
    def test_out_of_scope_ids_cover_the_top_25_gap_exactly(self):
        # every cwe-top-25 view member is either in this suite's catalog
        # union or explicitly out-of-scope -- nothing escapes either list.
        view_ids = CWE_TOP_25_VIEWS["cwe-top-25"]
        catalog_ids = {e.id for e in _UNION_CATALOG}
        out_of_scope_ids = {e.id for e in CWE_TOP_25_OUT_OF_SCOPE}
        assert out_of_scope_ids == view_ids - catalog_ids


class TestFiringFromParsedSurfaceSource:
    """T-0145: for every id whose `capability_kind` is set, its `.strata`
    vuln fixture -- run through the REAL `strata_core` parser, never a
    hand-built `KernelModel` -- fires an undischarged THREAT003 obligation
    against the declared node."""

    @pytest.mark.parametrize(
        "cwe_id",
        sorted(cwe for cwe, v in _FIRING_FIXTURES.items() if v is not None),
    )
    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0145
    def test_fires_undischarged(self, cwe_id: str):
        fixture = _FIRING_FIXTURES[cwe_id]
        assert fixture is not None
        filename, node_id = fixture
        model = _load_model(filename)
        result = check_discharge_completeness(model, catalog=_UNION_CATALOG)
        assert result.is_ok
        violations = {(v.cwe, v.node): v for v in result.danger_ok}
        assert (cwe_id, node_id) in violations
        assert violations[(cwe_id, node_id)].rule == "THREAT003"


class TestHardenedDischargesFromParsedSurfaceSource:
    """T-0145: for every id with a hardened twin, the SAME obligation that
    fires in the vuln fixture is discharged (absent from THREAT003
    violations) in the hardened fixture -- parsed the same way, never a
    hand-built `KernelModel`."""

    @pytest.mark.parametrize("cwe_id", sorted(_HARDENED_FIXTURES))
    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0145
    def test_discharges_cleanly(self, cwe_id: str):
        filename, node_id = _HARDENED_FIXTURES[cwe_id]
        model = _load_model(filename)
        result = check_discharge_completeness(model, catalog=_UNION_CATALOG)
        assert result.is_ok
        cwes_undischarged = {v.cwe for v in result.danger_ok}
        assert cwe_id not in cwes_undischarged


class TestSharedExecCapabilityDischargesIndependently:
    """T-0145: `cwe_exec_vuln.strata`/`cwe_exec_hardened.strata` join
    CWE-78 and CWE-94 on the SAME `may "exec"` capability
    (`test_cwe_94_reuses_the_exec_capability_join`'s precedent,
    test_threat.py) -- these tests prove each fires/discharges
    independently of the other from ONE parsed fixture, not merely that
    the union of the two is empty."""

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0145
    def test_vuln_fixture_fires_both_independently(self):
        model = _load_model("cwe_exec_vuln.strata")
        result = check_discharge_completeness(model, catalog=_UNION_CATALOG)
        assert result.is_ok
        cwes = {v.cwe for v in result.danger_ok}
        assert "CWE-78" in cwes
        assert "CWE-94" in cwes

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0145
    def test_hardened_fixture_discharges_both_independently(self):
        model = _load_model("cwe_exec_hardened.strata")
        result = check_discharge_completeness(model, catalog=_UNION_CATALOG)
        assert result.is_ok
        cwes = {v.cwe for v in result.danger_ok}
        assert "CWE-78" not in cwes
        assert "CWE-94" not in cwes

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0145
    def test_discharging_only_one_leaves_the_other_undischarged(self):
        # A model that discharges CWE-78 alone must NOT accidentally
        # discharge CWE-94 (proves the two obligations join the shared
        # capability independently, not as one merged claim).
        text = (_LITMUS_DIR / "cwe_exec_hardened.strata").read_text(encoding="utf-8")
        # drop the CWE-94 discharge claim line, keep CWE-78's
        partial = "\n".join(
            line for line in text.splitlines() if 'weakness:CWE-94:runner"' not in line
        )
        module = parse_module(partial).danger_ok
        model = elaborate(module).danger_ok
        result = check_discharge_completeness(model, catalog=_UNION_CATALOG)
        assert result.is_ok
        cwes = {v.cwe for v in result.danger_ok}
        assert "CWE-78" not in cwes
        assert "CWE-94" in cwes


class TestCapabilityKindNoneEntriesNeverFireByDesign:
    """T-0145 design finding (docs/strata/threat.md#litmus-coverage):
    CWE-22/CWE-352/CWE-798 are cataloged with `capability_kind=None` --
    `_fired_obligations` only joins entries whose `capability_kind is not
    None`, so NO `.strata` source, however plausibly vulnerable-looking,
    can ever make these fire under THREAT003 today. Asserted explicitly
    against a real parsed fixture that models the vulnerable-looking
    scenario, rather than skipped."""

    @pytest.mark.parametrize("cwe_id", sorted(_UNFIRED_FIXTURES))
    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0145
    def test_never_fires_even_in_a_plausible_vulnerable_scenario(self, cwe_id: str):
        filename = _UNFIRED_FIXTURES[cwe_id]
        model = _load_model(filename)
        result = check_discharge_completeness(model, catalog=_UNION_CATALOG)
        assert result.is_ok
        cwes = {v.cwe for v in result.danger_ok}
        assert cwe_id not in cwes

    # frob:tests src/frob/strata/_threat.py::CWE_CATALOG kind="unit"
    # frob:ticket T-0145
    def test_capability_kind_is_none_for_all_three(self):
        by_id = {e.id: e for e in _UNION_CATALOG}
        for cwe_id in _UNFIRED_FIXTURES:
            assert by_id[cwe_id].capability_kind is None
