## Done report

T-4661 -- Gate registration interface: job list, known-rule set and check-coverage derived from one registry

WHAT changed
------------
- src/frob/gates/_registry.py (NEW): one gate registration interface.
  - RegistryError (typani ErrorSet): DuplicateJob, DuplicateRuleId, EmptyRuleIds.
  - GateRegistration (pydantic BaseModel, model_config = {}): job, rule_ids,
    stage_groups, severity, reads.
  - register_gate(): Result[GateRegistration, RegistryError] -- refuses a
    duplicate job name or a rule id already claimed by a different job.
  - gate(...) decorator form (raises RuntimeError on conflict -- no caller
    to hand a Result back to at import time).
  - seed_legacy_bulk(): idempotent one-time bulk seed of the CURRENT
    hand-maintained _ALL_GATES/_KNOWN_GATE_RULES as a single "legacy" entry
    (see MIGRATION POSTURE below).
  - reset_registry_for_tests(): test-only escape hatch.
  - Four derived views: derive_job_names(), derive_known_rule_ids(),
    derive_check_coverage_entries() (-> CheckCoverageEntry), and
    derive_doc_rule_table().
  - find_unregistered_live_rule_ids(): the GATERULE001-shaped completeness
    check, sourced from this registry (candidate scan injected as a
    callable, so this module has no import dependency on
    frob.gates._rule_id_scan or its leased neighbors).
  - Logging: every state change (register success/failure, seed, reset,
    unregistered-id detection) goes through the module logger at
    info/debug/warning/error as appropriate.

- tests/unit/test_gate_registry.py (NEW): 14 tests.
  - TestRegisterGate: success, duplicate job, duplicate rule id, empty
    rule ids.
  - TestGateDecorator: registers-and-returns-unchanged, raises on conflict.
  - TestSeedLegacyBulk: idempotence, refusal on different data.
  - TestDerivedViewsMatchLegacyExactly: derive_job_names()/derive_known_
    rule_ids() equal today's _ALL_GATES/_KNOWN_GATE_RULES exactly, once
    seeded -- acceptance [0].
  - TestAddingADetectorTouchesOneFile::test_adding_a_detector_touches_one_
    file -- POSITIVE CONTROL, acceptance [1]: registers a fake detector
    (FAKE_T4661_001) through the registry alone, asserts it appears in the
    derived job list, known-rule-id set and check-coverage view, and
    asserts the fake id was never written into gates/__init__.py or
    _waive.py's source text.
  - TestUnregisteredLiveRuleIsReported -- acceptance [2]: a registered id
    is not reported; an unregistered candidate id IS reported.
  - TestGateRegistrationDocDescribesTheFourDerivedViews -- acceptance [3]:
    the doc names register_gate and all four derive_* functions.

- docs/modules/gate-registration.md (NEW): the registration interface, the
  four derived views (table), the migration posture (why gates/__init__.py
  and _waive.py are not re-pointed yet), and a Reference section with one
  heading per public symbol (frob:doc anchor targets).

WHY
---
Measured this week: TESTMOCK001 (T-3997), RACE001/RACE002 (T-3953), SYS118
(T-3964), COV010 (T-4230), and SYS116/SYS117 (T-4612) each shipped UNWIRED
because gates/__init__.py and _waive.py were leased by other in-progress
tickets when the detector landed -- spawning the T-4647/T-4605 fold-in
tickets purely to wire already-finished work in after the fact. This
leaf gives a detector ONE registration call from which the job list, the
known-rule-id set, the doc rule table, and the check-coverage entries are
all derived, so a future detector cannot repeat that failure mode.

MIGRATION POSTURE / DISCLOSED SCOPE BOUNDARY (per BRIEF.md's lease
guidance)
---------------------------------------------------------------------
gates/__init__.py is leased by T-3962; _waive.py is leased by T-4112/
T-4113/T-4212/T-4420/T-4632 (checked via `grep -l "_waive.py"
.git/frob-leases/*.json` from ROOT before starting). Per the coordinator's
explicit instruction, this leaf does NOT touch either file: it builds the
registry as a new module (_registry.py) plus its own tests and doc, and
seed_legacy_bulk() proves the derived views equal today's hand-maintained
_ALL_GATES/_KNOWN_GATE_RULES by test, without editing them. The one-line
wiring hunk (re-pointing gates/__init__.py's job list and _waive.py's
_KNOWN_GATE_RULES at these derived views) is already tracked by T-4647 --
filed nothing new for it, per BRIEF.md's instruction.

Evidence (bound AFTER the last commit, per checklist item 8)
--------------------------------------------------------------
Acceptance [1] (job list/rule set equal legacy exactly):
  tests/unit/test_gate_registry.py::TestDerivedViewsMatchLegacyExactly::test_derived_job_names_equal_all_gates
  tests/unit/test_gate_registry.py::TestDerivedViewsMatchLegacyExactly::test_derived_known_rule_ids_equal_known_gate_rules
Acceptance [2] (positive control):
  tests/unit/test_gate_registry.py::TestAddingADetectorTouchesOneFile::test_adding_a_detector_touches_one_file
Acceptance [3] (unregistered live rule reported):
  tests/unit/test_gate_registry.py::TestUnregisteredLiveRuleIsReported::test_unregistered_live_rule_is_reported
Acceptance [4] (doc describes interface + four derived views):
  tests/unit/test_gate_registry.py::TestGateRegistrationDocDescribesTheFourDerivedViews::test_doc_describes_registration_interface_and_derived_views

(Ticket brief's own acceptance list is 0-indexed [0]-[3]; `frob ticket
evidence --accepts` is 1-indexed, so the above map to --accepts 1..4
respectively -- confirmed by the tool's own error message when I first
tried --accepts 0.)

Filed: none (T-4647 already tracks the gates/__init__.py/_waive.py wiring
disclosed above; no other out-of-scope work found).

Commits (worktree /home/logan/projects/frob/.claude/worktrees/t-4661,
branch t-4661):
  dbfcb35b5  feat(gates): add gate registration interface (T-4661)
  6dd5a2169  test(gates): add doc-content evidence test for T-4661 acceptance [3]
  a1e47a6ea, 58620aee3, b9e89421c  chore(tickets): record evidence for T-4661 (evidence binds after last code commit)
HEAD sha: b9e89421c85ed7422a9fe43f37d9a3069dc6fe7c

## Pre-READY checks

1. `frob check --only sys --files src/frob/gates/_registry.py --files tests/unit/test_gate_registry.py --files docs/modules/gate-registration.md --base dev`:
   Tool summary showed FAIL gate:DRIFT (6 errors, pre-existing in
   src/frob/tickets/_evidence.py, unrelated to my files, waived in output)
   and FAIL gate:DSL (1 error, also unrelated -- grep of the full output
   for "_registry.py|test_gate_registry.py|gate-registration.md" returned
   ZERO matches, confirming no finding is attributable to my files).
   Result: no SELFAUDIT001 or any other finding against my files.

2. `frob check --only arch --files src/frob/gates/_registry.py --files tests/unit/test_gate_registry.py --files docs/modules/gate-registration.md --base dev`:
   "pass  frob-arch  19 warnings (36 waived), 546 suggestions" -- grep for
   my three files across the full output returned ZERO matches: no
   ARCH001/LARGE001 against my files.

3. `frob check --only coverage --files src/frob/gates/_registry.py --files tests/unit/test_gate_registry.py --files docs/modules/gate-registration.md --base dev` (re-run after adding frob:doc anchors + Reference section headers):
   grep of the full output for "_registry.py|test_gate_registry.py|gate-registration.md"
   returned ZERO matches: no COV001/COV002/COV00x against my files (the
   remaining FAIL gate:COV/TODO/DSL/DRIFT lines in the tool summary are
   all pre-existing findings in other files, e.g. src/frob/vet/_registry.py,
   src/frob/tickets/_evidence.py -- unrelated to this ticket's scope).

4. `ty check src/frob/gates/_registry.py tests/unit/test_gate_registry.py`:
   "All checks passed!"
   `ruff check src/frob/gates/_registry.py tests/unit/test_gate_registry.py`:
   "All checks passed!"

5. Cross-ticket file check: `git diff --name-only dev...HEAD` (code
   commits only) = src/frob/gates/_registry.py, tests/unit/test_gate_registry.py,
   docs/modules/gate-registration.md -- all three are exactly this
   ticket's own declared scope (.git/frob-leases/T-4661.json); none is
   leased by any other in-progress ticket (grep -l over
   .git/frob-leases/*.json for each of the three paths returned only
   T-4661's own lease file).

6. Not a kind=bug ticket -- BUG002 designate-repro step not applicable.

7. tickets/ directory: no tickets/T-draft-* created by this ticket; T-4661's
   id: line already matches its directory from the pre-existing ledger
   (this ticket was pre-filed by the epic/story planning pass, not created
   fresh in this worktree).

8. Evidence bound AFTER the last commit: the final evidence-recording
   commit (b9e89421c) is the tip of the branch; no code commit follows it.

Pytest run (all 14 tests in the new file, local sanity check before
binding evidence):
  PYTHONPATH=.../t-4661/src python -m pytest tests/unit/test_gate_registry.py -p no:cacheprovider -q
  -> SUITE-RESULT: exitstatus=0 collected=14 failed=0

### Changed
```
 docs/modules/gate-registration.md |  174 +++
 src/frob/gates/_registry.py       |  317 +++++
 tests/unit/test_gate_registry.py  |  226 ++++
 tickets/T-4661/done-report.md     | 2364 +++++++++++++++++++++++++++++++++++++
 tickets/T-4661/ticket.md          |   25 +-
 5 files changed, 3100 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_gate_registry.py::TestAddingADetectorTouchesOneFile::test_adding_a_detector_touches_one_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_gate_registry.py::TestUnregisteredLiveRuleIsReported::test_unregistered_live_rule_is_reported` (pytest node id, verified passing when recorded)
- `tests/unit/test_gate_registry.py::TestDerivedViewsMatchLegacyExactly::test_derived_job_names_equal_all_gates` (pytest node id, verified passing when recorded)
- `tests/unit/test_gate_registry.py::TestDerivedViewsMatchLegacyExactly::test_derived_known_rule_ids_equal_known_gate_rules` (pytest node id, verified passing when recorded)
- `tests/unit/test_gate_registry.py::TestGateRegistrationDocDescribesTheFourDerivedViews::test_doc_describes_registration_interface_and_derived_views` (pytest node id, verified passing when recorded)
