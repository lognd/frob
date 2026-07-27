# frob:waive SCOPE001 reason="T-0658's declared scope is src/frob/strata/**+docs/design/registry/system-design.yaml+tests/unit/strata/**; this test module lives in tests/unit/strata/ per that scope, but the registry loader/gate machinery it exercises (frob.registry, frob.gates._registry_exhaustiveness) is shared infrastructure this ticket does not own, same ad-hoc precedent as tests/test_registry_reconciliation_system_design.py's T-0392 SCOPE001 waiver"  # noqa: E501
"""T-0658 (epic T-0331's N:M coverage close condition): binds every
`docs/design/registry/system-design.yaml` entry (the system-design-corpus.md
denominator) to a real disposition -- a registered SYS2xx/REL2xx check
(`handled_by:RULE`) or a reasoned deferral/exclusion (`deferred:T-XXXX` /
`out_of_scope:...` / `duplicate-of-artifact`) -- so the epic's obligation
families (T-0640..T-0656, REL2xx-REL39x + SYS200-204) have a live,
checkable claim of coverage against the corpus they were built to satisfy,
not just a design-doc assertion.

This mirrors T-0392's `tests/test_registry_reconciliation_system_design.py`
in shape (same live-data pin over the same file) but is owned separately,
under T-0331/T-0658's own scope and test tree: T-0392 was the one-time
reconciliation PASS that got system-design.yaml to a fully-dispositioned
state; this module is the epic's own standing closing evidence that the
state T-0392 reached (and every SYS2xx/REL2xx-emitting ticket since) has
not silently regressed. The drift-lock MECHANISM itself (an undispositioned
entry fails the gate) is proven generically, over synthetic fixtures, by
`tests/test_registry_exhaustiveness.py::TestDisposition::
test_undispositioned_entry_fails` and `TestTotalDrift::
test_total_mismatch_fails` -- not re-proven here; this module only pins
that the mechanism, applied to the REAL system-design.yaml, currently
reports zero unaccounted entries and zero registry_gate violations."""

from __future__ import annotations

from pathlib import Path

from frob.gates import known_gate_rule_ids
from frob.gates._registry_exhaustiveness import registry_gate
from frob.registry import DispositionKind, audit_registry_file, load_registry_dir
from frob.tickets import load_queue
from frob.tickets._models import TicketQueue

# frob:ticket T-0658
_REPO_ROOT = Path(__file__).resolve().parents[3]
# frob:ticket T-0658
_REGISTRY_DIR = _REPO_ROOT / "docs" / "design" / "registry"
# frob:ticket T-0658
_SYSTEM_DESIGN_CATALOGUED_TOTAL = 119


# frob:ticket T-0658
def _real_queue() -> TicketQueue:
    """The repo's real, live ticket queue -- falls back to an empty queue
    only if the ledger itself fails to parse, so a real deferred-to-
    missing-ticket regression is never masked by a queue too small to
    notice it (mirrors `test_registry_reconciliation_system_design.py`'s
    own helper)."""
    loaded = load_queue(_REPO_ROOT)
    return loaded.danger_ok if loaded.is_ok else TicketQueue(tickets={})


# frob:ticket T-0658
def _load_system_design():
    """The real, live `system-design.yaml` `RegistryFile` this module's
    every test reads."""
    return load_registry_dir(_REGISTRY_DIR, ("system-design.yaml",))[
        "system-design.yaml"
    ].danger_ok


# frob:ticket T-0658
# frob:tests tests/unit/strata/test_system_design_coverage.py::TestSystemDesignCorpusCoverage.test_every_corpus_entry_is_dispositioned_and_total_matches  # noqa: E501
# frob:tests tests/unit/strata/test_system_design_coverage.py::TestSystemDesignCorpusCoverage.test_at_least_one_systems_checks_family_rule_is_bound  # noqa: E501
class TestSystemDesignCorpusCoverage:
    """T-0658 acceptance [0]: every `system-design-corpus.md` denominator
    entry has a disposition, and coverage total matches the declared
    TOTAL -- pinned against the real file, not a fixture standing in for
    it (`audit_registry_file`'s `exhausted`/`unaccounted` fields are the
    single source of truth this whole module reads)."""

    # frob:ticket T-0658
    # frob:waive DUP001 reason="shares the same audit_registry_file(total/exhausted/unaccounted) assertion shape every sibling registry-domain reconciliation test uses (test_registry_reconciliation_system_design.py/supply_chain.py/evasion.py/weaknesses.py/...) -- each one pins a DIFFERENT registry file's own live state as that domain's own standing evidence; T-0658 owns this one for system-design.yaml specifically under the epic's own scope/test tree (see module docstring), extracting a shared helper across ~10 independently-scoped reconciliation tickets is a real but separate refactor, not this ticket's job"  # noqa: E501
    def test_every_corpus_entry_is_dispositioned_and_total_matches(self) -> None:
        """`audit.exhausted is True` and `audit.unaccounted == 0`: every
        one of the 119 catalogued entries (105 genuine + 14 manifest-
        extraction artifacts, RECONCILIATION.md finding (d)) resolves to
        `handled` (a registered SYS2xx/REL2xx check), `deferred` (an open
        ticket), `duplicate` (an artifact), or `out_of_scope` (a reasoned
        exclusion) -- never silently uncounted."""
        registry_file = _load_system_design()
        audit = audit_registry_file(registry_file)

        assert audit.total == _SYSTEM_DESIGN_CATALOGUED_TOTAL
        assert audit.exhausted is True
        assert audit.unaccounted == 0
        assert (
            audit.handled + audit.deferred + audit.duplicate + audit.out_of_scope
            == _SYSTEM_DESIGN_CATALOGUED_TOTAL
        )

    # frob:ticket T-0658
    # frob:waive DUP001 reason="shares a set-comprehension-over-entry_lists shape with sibling reconciliation tests' test_no_entry_defers_to_this_reconciliation_ticket (each pins a DIFFERENT registry file's own disposition-target set for a DIFFERENT reason -- theirs excludes a self-referential ticket id, this asserts a SYS2xx/REL2xx-family target exists); same cross-domain-refactor deferral as this class's other DUP001 waiver above"  # noqa: E501
    def test_at_least_one_systems_checks_family_rule_is_bound(self) -> None:
        """At least one `handled_by:RULE` disposition names a REL2xx/
        SYS2xx-family rule id (the epic's own obligation families,
        T-0640..T-0656 + T-0392) -- guards against the corpus's
        `handled` count being entirely non-systems-checks rules, which
        would satisfy `test_every_corpus_entry_is_dispositioned_and_
        total_matches` vacuously for THIS epic's own close condition even
        though the file is exhausted overall."""
        registry_file = _load_system_design()
        handled_targets = {
            entry.disposition.target
            for entries in registry_file.entry_lists.values()
            for entry in entries
            if entry.disposition.kind is DispositionKind.HANDLED_BY
        }
        systems_checks_targets = {
            target
            for target in handled_targets
            if target is not None
            and (target.startswith("SYS2") or target.startswith("REL2"))
        }
        assert systems_checks_targets, (
            f"expected >=1 SYS2xx/REL2xx-bound entry, got handled_by targets: "
            f"{sorted(handled_targets)}"
        )


# frob:ticket T-0658
# frob:tests tests/unit/strata/test_system_design_coverage.py::TestSystemDesignGateLiveZero.test_no_system_design_violations  # noqa: E501
class TestSystemDesignGateLiveZero:
    """T-0658 acceptance [1]: a future new `system-design-corpus.md` entry
    with no disposition fails the build -- verified here by confirming the
    REAL gate (`registry_gate`, wired into `frob check`'s default gate
    run) reports zero violations for `system-design.yaml` TODAY, over the
    live ticket queue, so any future drift (an undispositioned addition,
    a deferral rotting to a closed ticket, a dangling `handled_by`) has
    somewhere to regress FROM -- the generic drift-lock mechanism itself
    (an undispositioned/mismatched-total fixture actually failing
    `registry_gate`) is proven in `tests/test_registry_exhaustiveness.py`,
    not re-proven here."""

    # frob:ticket T-0658
    def test_no_system_design_violations(self) -> None:
        real_queue = _real_queue()

        violations = registry_gate(
            _REPO_ROOT, real_queue, known_gate_rule_ids(), _REGISTRY_DIR
        )
        system_design_violations = [
            v for v in violations if v.file == "docs/design/registry/system-design.yaml"
        ]

        assert system_design_violations == []
