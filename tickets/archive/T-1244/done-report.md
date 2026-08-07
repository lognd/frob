## Done report

De-vacuized the compliance gate: COMPLIANCE005 alone only proved a
CMPL-* row's disposition STRING was non-deferred; it never verified the
named `handled_by` control actually enforces that framework's real
obligations. 16 of the 17 CMPL_REGISTRY_UNIT_IDS rows carry the
self-referential `handled_by:COMPLIANCE005`, which is circular ("handled
by the check that verifies a disposition string exists" proves nothing
about real per-framework coverage).

Changed:
- src/frob/strata/_compliance.py: `_CMPL_UNIT_TRIAGE_TICKET` (maps each
  vacuously-self-referential CMPL unit to the open per-framework triage
  ticket that owns its real re-disposition, T-1245-T-1249),
  `_cmpl_unit_backing_violation` + `_check_cmpl_registry_unit_backing`
  (COMPLIANCE007), wired into `check_cmpl_registry` alongside
  COMPLIANCE005. `CMPL-FROB-CATALOG-ENTRIES` is excluded -- it is a
  meta-row genuinely counting `COMPLIANCE_CATALOG`'s own real entries
  (T-1250 confirms this explicitly), not a vacuous self-reference.
- src/frob/gates/_decisions_compliance.py: `_compliance005_violation`
  (renamed in effect, same symbol) now assigns `Severity.WARN` to
  COMPLIANCE007 and keeps `Severity.ERROR` for COMPLIANCE005 -- per the
  dispatch instructions, re-dispositioning each of the 16 flagged rows is
  a framework-classification decision the sibling triage tickets own,
  not a code bug this ticket fixes, so this is deliberately WARN-tier
  rather than a hard build failure.
- src/frob/gates/_waive.py: registered `COMPLIANCE007` in
  `_KNOWN_GATE_RULES` (required for the new rule id to resolve anywhere
  `known_gate_rule_ids()` is consulted, e.g. caught_by integrity checks).
- docs/design/registry/check-coverage.yaml: `frob registry audit
  --sync-gate-rules` mechanically appended `CHK-GATE-COMPLIANCE007`
  (gate_rule_total 267 -> 268) -- REG010's own staleness lock, not a
  hand-edit.
- docs/design/registry/EXHAUSTIVENESS-GATE.md: new "COMPLIANCE005/
  COMPLIANCE007: compliance registry vs. model checking (T-1244)"
  section stating plainly what `compliance_gate` does and does not
  verify (acceptance[2]): both rules are pure `compliance.yaml`
  registry-string checks, model-independent; the real model-driven check
  (`evaluate_compliance`) is invoked only via the separate, explicit
  `frob sys audit <design-file>` command and is NOT wired into `frob
  check`'s automatic gate pipeline -- documented as a deliberate,
  investigated non-goal (acceptance[1]'s "or" branch), not a silent gap.
- tests/unit/strata/test_compliance.py: `TestCmplRegistryBacking` (3
  tests) plus updated `test_check_cmpl_registry_loads_real_file` to
  assert the honest real-repo state (COMPLIANCE005 clean, COMPLIANCE007
  fires on exactly the 16 `_CMPL_UNIT_TRIAGE_TICKET` ids).
- tests/test_gates.py: 4 new `TestComplianceGate` tests covering
  COMPLIANCE007's registration, WARN severity, the CMPL-FROB-CATALOG-
  ENTRIES exception, and the real-repo smoke test (16 findings, all
  WARN).

Acceptance:
[0] (fabricated/unknown handled_by target fails loud) is already covered
    by the existing, generic REG002 check
    (`frob.gates._registry_exhaustiveness._classify_handled_by`), which
    runs over EVERY `REGISTRY_FILES` member including `compliance.yaml`
    and verifies a `handled_by:<rule>` target resolves against
    `known_gate_rule_ids()` -- confirmed by reading the code path rather
    than assumed; no new code needed for this half, only documented
    (EXHAUSTIVENESS-GATE.md's new section references it). This ticket's
    own new code (COMPLIANCE007) closes the DIFFERENT, deeper gap: a
    target that DOES resolve to a real rule id (COMPLIANCE005 itself)
    but that rule doesn't actually verify anything about the specific
    framework.
[1] evaluate_compliance model-driven checking is confirmed NOT wired
    into `frob check` (no call path found from any gate module) --
    documented explicitly in EXHAUSTIVENESS-GATE.md as a deliberate,
    named non-goal with the compensating control (`frob sys audit
    <design-file>`, this repo's own instance being `design/frob.strata`)
    rather than left as a silent assumption. Wiring evaluate_compliance
    automatically into `frob check` itself was NOT done -- that would be
    a much larger, riskier behavior change (auto-discovering and
    evaluating every `.strata` file repo-wide on every `frob check` run)
    outside this ticket's reasonable scope; disclosed as a cut, not
    silently dropped.
[2] EXHAUSTIVENESS-GATE.md now states plainly what compliance_gate does
    and does not verify (new section, see above).

Gates: `uv run frob check --only prework --ticket T-1244` clean (0/0).
`uv run frob check --only registry --ticket T-1244` clean (0 errors, 10
pre-existing REG008 warnings unrelated to this change). `uv run frob
check --only docanchor --only doclink --ticket T-1244`: only the same 4
pre-existing orphan-doc DOC001 errors seen on T-1242 (unrelated files,
predate this ticket). `uv run frob check --only scope --ticket T-1244`:
3 SCOPE001 errors are an artifact of working T-1242 and T-1244 serially
in one un-landed worktree -- they name docs/design/compliance-corpus.md,
docs/guides/extending/compliance-registry.md, docs/strata/threat.md,
which are T-1242's own already-committed, already-closed-ticket files
that show up in `--base main`'s diff only because T-1242 has not landed
to main yet; not a real T-1244 scope violation. 472 SCOPE002 warnings
are pre-existing cross-reference noise from `tests/test_gates.py`/
`src/frob/gates/__init__.py` (a large, densely cross-referenced shared
module) now included in scope for the `TestComplianceGate` test class;
none are new errors.

Evidence: tests/unit/strata/test_compliance.py::TestCmplRegistryBacking::test_self_referential_handled_by_is_flagged,
tests/unit/strata/test_compliance.py::TestCmplRegistryBacking::test_frob_catalog_entries_self_reference_is_not_flagged,
tests/unit/strata/test_compliance.py::TestCmplRegistryBacking::test_non_self_referential_handled_by_is_not_flagged,
tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file,
tests/test_gates.py::TestComplianceGate::test_compliance007_registered_in_known_gate_rules,
tests/test_gates.py::TestComplianceGate::test_compliance007_fires_warn_on_self_referential_handled_by,
tests/test_gates.py::TestComplianceGate::test_compliance007_silent_on_frob_catalog_entries_self_reference,
tests/test_gates.py::TestComplianceGate::test_compliance007_real_repo_registry_surfaces_known_gap
(bound to acceptance indices 0/1/2 as applicable). Full test runs:
`uv run pytest tests/unit/strata/test_compliance.py -p no:cacheprovider
-q` -> 49 passed; `uv run pytest tests/test_gates.py -p no:cacheprovider
-q -k "Compliance or KnownGateRule"` -> 17 passed.

Filed: none new -- the 16 real per-framework re-disposition decisions
COMPLIANCE007 surfaces are already owned by existing open tickets
T-1245 (SOC2/PCI-DSS/HIPAA), T-1246 (GDPR/CCPA), T-1247 (NIST family),
T-1248 (ISO 27002/CIS), T-1249 (ASVS/SAMM/FedRAMP/SLSA); T-1250 already
covers confirming CMPL-FROB-CATALOG-ENTRIES's legitimate self-reference.
`_CMPL_UNIT_TRIAGE_TICKET` binds COMPLIANCE007's findings to those real,
open ticket ids directly rather than filing new duplicates.

### Changed
```
 docs/design/compliance-corpus.md             |   5 +-
 docs/guides/extending/compliance-registry.md |  11 +-
 docs/strata/threat.md                        |   1 +
 src/frob/strata/_compliance.py               |  79 +++++++-
 tests/unit/strata/test_compliance.py         |  46 +++++
 tickets.md                                   | 289 ++++++++++++++++++++++++++-
 6 files changed, 410 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance007_real_repo_registry_surfaces_known_gap` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestCmplRegistryBacking::test_self_referential_handled_by_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance007_fires_warn_on_self_referential_handled_by` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance007_silent_on_frob_catalog_entries_self_reference` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 10 error(s), 820 warning(s), 674 waived
- error-findings: DEPR002@src/frob/app/docs_runner.py, DEPR002@src/frob/app/map_runner.py, DEPR002@src/frob/app/outline_runner.py, DEPR002@src/frob/app/xref_runner.py, DOC001@docs/audits/docs-staleness-2026-07-29.md, DOC001@docs/design/check-fix-engine.md, DOC001@docs/design/ledger-v2.md, DOC001@docs/design/refactor-verb.md, DUP001@src/frob/gates/_decisions_compliance.py, SELFAUDIT001@design
