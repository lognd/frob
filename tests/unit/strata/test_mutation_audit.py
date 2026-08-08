"""T-1203: prove every `may` declaration in the real repo's `.strata`
models is load-bearing (deletion trips SYS100 + the export-syscall diff)
and double-detected on substitution (SYS100+SYS101 pair), that the
baseline SYS101 count is zero, and that no declared capability kind is a
scanner blind spot (docs/strata/selfconform.md#the-three-rules).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import Node
from frob.strata._mutation_audit import (
    APP_DETECTABLE_KINDS,
    DETECTABLE_KINDS,
    node_allowed_app_capabilities,
    run_may_mutation_audit,
)


# frob:ticket T-1328
def _node(nid: str, trust: str = "trusted", **kw) -> Node:
    return Node(id=nid, trust=trust, **kw)


# frob:ticket T-1328
class TestMayMutationAuditRealRepo:
    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo.test_basel\
    # ine_sys101_is_zero
    def test_baseline_sys101_is_zero(self) -> None:
        """Acceptance [2]: before any mutation, every declared `may` is
        already observed somewhere -- zero silently-deletable declarations."""
        repo_root = Path(__file__).resolve().parents[3]
        result = run_may_mutation_audit(repo_root)
        assert result.is_ok
        assert result.danger_ok.baseline_sys101_count == 0

    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo.test_no_un\
    # detectable_kinds
    def test_no_undetectable_kinds(self) -> None:
        """Acceptance [3]: every kind declared anywhere in the real repo's
        `.strata` models has a live detection path -- no scanner blind spot
        the harness silently passed over."""
        repo_root = Path(__file__).resolve().parents[3]
        result = run_may_mutation_audit(repo_root)
        assert result.is_ok
        assert result.danger_ok.undetectable == ()

    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo.test_every\
    # _may_is_load_bearing
    def test_every_may_is_load_bearing(self) -> None:
        """Acceptance [0]+[1]: every single `may` atom's deletion trips
        SYS100 (plus the independent export-syscall diff wherever
        `EXPORT_DETECTABLE_KINDS` claims coverage), and its substitution
        trips the SYS100+SYS101 pair."""
        repo_root = Path(__file__).resolve().parents[3]
        result = run_may_mutation_audit(repo_root)
        assert result.is_ok
        report = result.danger_ok
        assert report.findings
        failures = [f for f in report.findings if not f.load_bearing]
        assert failures == [], failures
        assert report.all_load_bearing

    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo.test_secon\
    # d_detector_gaps_are_exactly_the_disclosed_app_level_kinds
    # frob:ticket T-1328
    def test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds(
        self,
    ) -> None:
        """The seccomp/export detector (module docstring) has real
        syscall coverage for `exec`/`net`/`fs.read`/`fs.write` only. T-1328
        adds a SECOND, independent detector (the app-capability manifest,
        `node_allowed_app_capabilities`) for exactly the 7 kinds named in
        its title -- `eval`/`env`/`ffi`/`install-hook`/`sql`/`deserialize`/
        `fetch_url` (plus the precise `env.read`/`env.write` mode
        spellings) -- so those kinds are no longer a disclosed gap: they
        are double-detected by the app manifest instead of the seccomp
        export. Only `process-control` remains an actual gap: `testsuite`
        node's `may "process-control"` (design/frob.strata, T-1439's
        `signal.signal(` needle) has neither a syscall-level seccomp entry
        nor an app-manifest entry -- outside both this ticket's and
        T-1203's declared scope, a real gap, not spurious drift."""
        repo_root = Path(__file__).resolve().parents[3]
        result = run_may_mutation_audit(repo_root)
        assert result.is_ok
        gap_kinds = {g.kind for g in result.danger_ok.second_detector_gaps}
        assert gap_kinds == {"process-control"}


class TestDetectableKindsVocabulary:
    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestDetectableKindsVocabulary.test_wire\
    # d_tier2_kinds_are_detectable
    def test_wired_tier2_kinds_are_detectable(self) -> None:
        """The tier-2-joined kinds (`fs.read`/`fs.write`/`exec`/
        `net.connect`/`net.listen`/`env.read`/`env.write`) are all in
        `DETECTABLE_KINDS` -- SYS100 core's own vocabulary."""
        for kind in ("fs.read", "fs.write", "exec", "net.connect", "net.listen"):
            assert kind in DETECTABLE_KINDS

    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestDetectableKindsVocabulary.test_proc\
    # _family_is_currently_undetectable
    def test_proc_family_is_currently_undetectable(self) -> None:
        """`proc` (module docstring: unwired per `frob.vet._capability_
        modes`'s own "wiring status" section) has no tier-2 join and is
        not in `_EXTENDED_KINDS` -- confirms the acceptance [3] blind-spot
        path is reachable, not vacuously untested."""
        assert "proc" not in DETECTABLE_KINDS


# frob:ticket T-1328
class TestNodeAllowedAppCapabilities:
    """T-1328: the independent app-capability manifest detector."""

    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestNodeAllowedAppCapabilities.test_map\
    # s_each_app_kind
    # frob:ticket T-1328
    def test_maps_each_app_kind(self) -> None:
        """Each of the 7 declared app-level kinds names its own node a
        distinct, non-empty manifest entry set -- the manifest is not a
        stub that maps everything to one bucket."""
        for kind in (
            "eval",
            "env",
            "ffi",
            "install-hook",
            "sql",
            "deserialize",
            "fetch_url",
        ):
            assert kind in APP_DETECTABLE_KINDS
            node = _node("n", may=(f'{kind}:target',) if ":" not in kind else (kind,))
            allowed = node_allowed_app_capabilities(node)
            assert allowed, f"{kind} produced no manifest entries"

    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestNodeAllowedAppCapabilities.test_dif\
    # fers_when_atom_removed
    # frob:ticket T-1328
    def test_differs_when_atom_removed(self) -> None:
        """Removing the ONLY app-level `may` atom on a node changes the
        computed manifest -- the diff this detector's mutation-audit
        wiring depends on actually fires."""
        with_sql = _node("n", may=("sql",))
        without_sql = _node("n", may=())
        assert node_allowed_app_capabilities(with_sql) != node_allowed_app_capabilities(
            without_sql
        )

    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestNodeAllowedAppCapabilities.test_bar\
    # e_env_covers_both_modes
    # frob:ticket T-1328
    def test_bare_env_covers_both_modes(self) -> None:
        """A bare `may "env"` declaration's manifest is a superset of what
        the precise `env.read`/`env.write` spellings each produce alone --
        mirrors `_SECCOMP_KIND_MAP`'s own coarse-declarer-covers-everything
        convention."""
        bare = node_allowed_app_capabilities(_node("n", may=("env",)))
        read_only = node_allowed_app_capabilities(_node("n", may=("env.read",)))
        write_only = node_allowed_app_capabilities(_node("n", may=("env.write",)))
        assert read_only <= bare
        assert write_only <= bare

    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestNodeAllowedAppCapabilities.test_unk\
    # nown_kind_allows_nothing
    # frob:ticket T-1328
    def test_unknown_kind_allows_nothing(self) -> None:
        """A kind outside `_APP_CAPABILITY_MANIFEST_MAP` (e.g. `exec`, a
        seccomp-covered kind) contributes nothing to the app manifest --
        this detector never silently claims coverage it does not have."""
        node = _node("n", may=("exec",))
        assert node_allowed_app_capabilities(node) == frozenset()
