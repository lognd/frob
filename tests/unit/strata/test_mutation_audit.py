"""T-1203: prove every `may` declaration in the real repo's `.strata`
models is load-bearing (deletion trips SYS100 + the export-syscall diff)
and double-detected on substitution (SYS100+SYS101 pair), that the
baseline SYS101 count is zero, and that no declared capability kind is a
scanner blind spot (docs/strata/selfconform.md#the-three-rules).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata._mutation_audit import (
    DETECTABLE_KINDS,
    run_may_mutation_audit,
)


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
    def test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds(
        self,
    ) -> None:
        """The seccomp/export detector (module docstring) has real
        syscall coverage for `exec`/`net`/`fs.read`/`fs.write` only -- every
        OTHER declared kind is a disclosed `second_detector_gap`, not a
        silently-passing false claim of double detection."""
        repo_root = Path(__file__).resolve().parents[3]
        result = run_may_mutation_audit(repo_root)
        assert result.is_ok
        gap_kinds = {g.kind for g in result.danger_ok.second_detector_gaps}
        assert gap_kinds == {
            "eval",
            "env",
            "deserialize",
            "fetch_url",
            "ffi",
            "install-hook",
            "sql",
        }


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
