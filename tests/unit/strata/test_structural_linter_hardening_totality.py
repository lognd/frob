"""T-0672: N:M meta-test binding `docs/design/structural-linter-
adversarial-hardening.md`'s denominator (5 named principles + 9
arch-evasion rows + 9 strata-evasion rows = 23 entries, RECONCILIATION.md
finding (a)) to `docs/design/registry/arch-checks.yaml`'s `SLH-RULE-*`/
`SLH-ARCH-EVA-*`/`SLH-SYS-EVA-*` entries -- the T-0341 epic's close
condition.

Same real-data posture as the sibling reconciliation pin tests
(`tests/test_registry_reconciliation_*.py`, T-0384-T-0392): this loads
the REAL registry file, not a synthetic fixture, so a drift between the
hardening doc's corpus and the registry's own SLH-* catalogue fails the
build rather than a fixture standing in for it.

Acceptance criterion [0]: every SLH-* entry named by the denominator
below has a disposition -- `handled_by:<rule>` (addressed-by-check) or
`out_of_scope:...`/`deferred:...` (reasoned-deferral); `parse_disposition`
already treats a missing/blank/bare disposition as `UNDISPOSITIONED`, so
asserting `disposition.kind is not DispositionKind.UNDISPOSITIONED` for
every denominator id is the exact check.

Acceptance criterion [1]: a NEW hardening-doc entry with no matching
registry id fails the build. This module hardcodes `_DENOMINATOR_IDS`
(the corpus enumeration, mirroring `_SYSTEM_DESIGN_CATALOGUED_TOTAL`'s
own hardcoded-count precedent in `tests/test_registry_reconciliation_
system_design.py`) and asserts it is a SUBSET of the registry's real
SLH-* id set -- if a future corpus addition to the hardening doc is
never given a matching registry entry, the denominator here is edited to
add it (the SAME edit any of this ticket's sibling reconciliation tests
require, T-0343's drift-lock framework: the corpus is the enforceable
denominator, not just reading) and the test fails until the registry
entry exists, so the mismatch cannot go unnoticed.

The five conformance checks this epic built (SYS100/SYS103/SYS104/
SYS105/SYS106, T-0667-T-0670) are bound to their exact denominator rows:
`SLH-SYS-EVA-01` (unmodeled module) -> SYS103, `SLH-SYS-EVA-02` (under-
declared capability) -> SYS100, `SLH-SYS-EVA-03` (undeclared public
surface) -> SYS104, `SLH-SYS-EVA-04` (purpose drift) -> SYS105,
`SLH-SYS-EVA-05` (binding laundering) -> SYS106 -- verified directly
against the registry's own `disposition` string, not assumed."""

from __future__ import annotations

from pathlib import Path

from frob.registry import DispositionKind, audit_registry_file, load_registry_dir

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REGISTRY_DIR = _REPO_ROOT / "docs" / "design" / "registry"

#: The hardening doc's full corpus denominator (RECONCILIATION.md finding
#: (a)): 5 named principles + 9 arch-evasion table rows + 9 strata-
#: evasion table rows, each already minted a stable `SLH-*` id in
#: `arch-checks.yaml` at the time this ticket landed. Editing THIS list
#: is the intended response to a future corpus addition (module
#: docstring's acceptance criterion [1]) -- not silently ignoring the
#: resulting test failure.
_DENOMINATOR_IDS: frozenset[str] = frozenset(
    {
        "SLH-RULE-01-GROUND-TRUTH-GROUNDING",
        "SLH-RULE-02-MODEL-CODE-CONFORMANCE",
        "SLH-RULE-03-FAIL-CLOSED-UNPROVABLE",
        "SLH-RULE-04-BOUNDED-ESCAPE-HATCHES",
        "SLH-RULE-05-CONFIG-GATED",
        "SLH-ARCH-EVA-01-GODCLASS-SIDECAR-SPLIT",
        "SLH-ARCH-EVA-02-LONGFUNC-HELPER-SHATTER",
        "SLH-ARCH-EVA-03-LAYERING-REEXPORT-DI-DYNAMIC",
        "SLH-ARCH-EVA-04-FAKE-ABSTRACTION-SINGLE-IMPL",
        "SLH-ARCH-EVA-05-SRP-MANAGER-SERVICE-NAMING",
        "SLH-ARCH-EVA-06-FEATURE-FLAG-HIDE",
        "SLH-ARCH-EVA-07-GENERATED-MARKER-LAUNDER",
        "SLH-ARCH-EVA-08-WAIVE-EVERYTHING",
        "SLH-ARCH-EVA-09-THRESHOLD-LOWERING",
        "SLH-SYS-EVA-01-UNMODELED-MODULE",
        "SLH-SYS-EVA-02-UNDER-DECLARED-CAPABILITY",
        "SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE",
        "SLH-SYS-EVA-04-PURPOSE-DRIFT",
        "SLH-SYS-EVA-05-BINDING-LAUNDERING",
        "SLH-SYS-EVA-06-FLOW-BREAK",
        "SLH-SYS-EVA-07-FAKE-MITIGATION",
        "SLH-SYS-EVA-08-ASSUME-AWAY",
        "SLH-SYS-EVA-09-VIEW-NARROWING",
    }
)

#: The five conformance-check denominator rows this epic (T-0667-T-0670)
#: built a real, registered `frob sys audit` rule for -- each must carry
#: `handled_by:<that exact rule>` (addressed-by-check, not a reasoned
#: deferral) once its check exists, per this ticket's own mandate
#: ("binds ... to the five conformance checks built above").
_CONFORMANCE_CHECK_BINDINGS: dict[str, str] = {
    "SLH-SYS-EVA-01-UNMODELED-MODULE": "SYS103",
    "SLH-SYS-EVA-02-UNDER-DECLARED-CAPABILITY": "SYS100",
    "SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE": "SYS104",
    "SLH-SYS-EVA-04-PURPOSE-DRIFT": "SYS105",
    "SLH-SYS-EVA-05-BINDING-LAUNDERING": "SYS106",
}


def _real_slh_entries() -> dict[str, DispositionKind]:
    """Every real `SLH-*` entry id in `arch-checks.yaml` -> its parsed
    disposition kind, loaded from disk (never a fixture) -- the registry
    half of this test's N:M join."""
    loaded = load_registry_dir(_REGISTRY_DIR, ("arch-checks.yaml",))
    assert "arch-checks.yaml" in loaded, "arch-checks.yaml must exist"
    result = loaded["arch-checks.yaml"]
    assert result.is_ok, f"arch-checks.yaml failed to load: {result.err}"
    registry_file = result.danger_ok
    by_id: dict[str, DispositionKind] = {}
    for entries in registry_file.entry_lists.values():
        for entry in entries:
            if entry.id.startswith("SLH-"):
                by_id[entry.id] = entry.disposition.kind
    return by_id


def _real_slh_dispositions() -> dict[str, str]:
    """Every real `SLH-*` entry id -> its raw disposition STRING (not
    just the parsed kind) -- `TestConformanceChecksBoundToDenominator`
    needs the exact `handled_by:<rule>` target, not only whether it
    parsed as `HANDLED_BY`."""
    loaded = load_registry_dir(_REGISTRY_DIR, ("arch-checks.yaml",))
    registry_file = loaded["arch-checks.yaml"].danger_ok
    by_id: dict[str, str] = {}
    for entries in registry_file.entry_lists.values():
        for entry in entries:
            if entry.id.startswith("SLH-"):
                by_id[entry.id] = entry.disposition.raw
    return by_id


class TestDenominatorFullyDispositioned:
    """T-0672 acceptance criterion [0]."""

    # frob:tests tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned.test_every_denominator_id_has_a_real_registry_entry  # noqa: E501
    def test_every_denominator_id_has_a_real_registry_entry(self) -> None:
        """Every corpus id in `_DENOMINATOR_IDS` resolves to a real entry
        in `arch-checks.yaml` -- acceptance criterion [1]'s inverse: a
        denominator id with NO registry counterpart at all (not merely
        undispositioned, structurally absent) fails just as loudly."""
        real = _real_slh_entries()
        missing = _DENOMINATOR_IDS - real.keys()
        assert not missing, (
            f"denominator id(s) with no arch-checks.yaml entry at all: "
            f"{sorted(missing)}"
        )

    # frob:tests tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned.test_every_denominator_id_is_dispositioned  # noqa: E501
    def test_every_denominator_id_is_dispositioned(self) -> None:
        """Every corpus id's registry entry carries a REAL disposition
        (`handled_by`/`deferred`/`out_of_scope`/`duplicate_of`), never
        `UNDISPOSITIONED` -- acceptance criterion [0]."""
        real = _real_slh_entries()
        undispositioned = [
            entry_id
            for entry_id in sorted(_DENOMINATOR_IDS)
            if real.get(entry_id) is DispositionKind.UNDISPOSITIONED
        ]
        assert not undispositioned, (
            f"denominator id(s) with no disposition: {undispositioned}"
        )

    # frob:tests tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned.test_registry_has_no_extra_slh_entries_beyond_denominator  # noqa: E501
    def test_registry_has_no_extra_slh_entries_beyond_denominator(self) -> None:
        """The N:M totality direction acceptance criterion [1] guards
        against silently going stale in: `arch-checks.yaml` must not
        carry an `SLH-*` id the denominator here does not know about
        either (a registry entry with no corresponding doc row would be
        a fabricated citation, the same failure mode T-0343's framework
        exists to prevent in the other direction)."""
        real = _real_slh_entries()
        extra = real.keys() - _DENOMINATOR_IDS
        assert not extra, (
            f"arch-checks.yaml SLH-* id(s) not in the denominator: {sorted(extra)}"
        )

    # frob:tests tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned.test_arch_checks_gate_reports_zero_unaccounted_slh_entries  # noqa: E501
    def test_arch_checks_gate_reports_zero_unaccounted_slh_entries(self) -> None:
        """`audit_registry_file` (the same accounting `frob registry
        audit`/`frob check --only registry` uses) reports `exhausted`
        for `arch-checks.yaml` as a whole -- the live-gate-visible form
        of this same totality claim, not just this test's own count."""
        loaded = load_registry_dir(_REGISTRY_DIR, ("arch-checks.yaml",))
        registry_file = loaded["arch-checks.yaml"].danger_ok
        audit = audit_registry_file(registry_file)
        assert audit.exhausted, (
            f"arch-checks.yaml is not exhausted: {audit.unaccounted} "
            f"unaccounted, {audit.malformed} malformed"
        )


class TestConformanceChecksBoundToDenominator:
    """T-0672's own mandate: bind the denominator to the FIVE
    conformance checks T-0667-T-0670 built, not just leave every
    SYS-evasion row as a generic reasoned deferral."""

    # frob:tests tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator.test_each_conformance_row_handled_by_its_real_check  # noqa: E501
    def test_each_conformance_row_handled_by_its_real_check(self) -> None:
        """Each of `_CONFORMANCE_CHECK_BINDINGS`' five denominator rows
        carries `disposition: "handled_by:<rule>"` naming EXACTLY the
        rule id this epic built for it -- addressed-by-check, not a
        reasoned deferral, now that the check is real."""
        raw = _real_slh_dispositions()
        for entry_id, rule in _CONFORMANCE_CHECK_BINDINGS.items():
            assert raw.get(entry_id) == f"handled_by:{rule}", (
                f"{entry_id} disposition is {raw.get(entry_id)!r}, "
                f"expected 'handled_by:{rule}'"
            )

    # frob:tests tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator.test_bound_rules_are_real_known_gate_rules  # noqa: E501
    def test_bound_rules_are_real_known_gate_rules(self) -> None:
        """Each rule id `_CONFORMANCE_CHECK_BINDINGS` names is a REAL,
        registered `frob check`/`frob sys audit` rule id -- a
        `handled_by:` target naming a rule that does not exist would be
        REG002's dangling-handled-by violation; this proves it directly,
        the same live check `test_registry_exhaustiveness.py::
        TestDisposition.test_handled_by_real_rule_passes` exercises on a
        fixture."""
        from frob.gates import known_gate_rule_ids

        known = known_gate_rule_ids()
        for rule in _CONFORMANCE_CHECK_BINDINGS.values():
            assert rule in known, f"{rule} is not a known gate rule id"
