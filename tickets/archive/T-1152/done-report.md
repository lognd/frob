## Done report

Extracted the evidence/transition family (T-1151/T-1103 residue) out of
src/frob/tickets/__init__.py into a new src/frob/tickets/_evidence.py module,
following the T-1103 per-family extraction pattern: verbatim moves, directives
intact, private module re-exported from __init__ via explicit imports, zero
caller-visible behavior change.

Moved: _has_done_report, _start_blockers, _transition_guard,
_open_descendant_ids, _done_transition_structural_guard,
_done_transition_guard, _done_transition_diff_derived_guard,
_recover_missing_evidence_for_done, transition, reverify_close_guard,
_sync_cross_worktree_lease, add_evidence, _check_evidence_resolution,
_check_evidence_passing, _append_evidence_and_write, run_cmd_evidence,
_CMD_EVIDENCE_PARSE_RE, reverify_cmd_evidence, _run_evidence_command,
_check_cmd_evidence_kind, add_cmd_evidence, render_evidence_block,
_EVIDENCE_LINE_RE, _parse_evidence_ids_from_done_report,
replay_evidence_from_done_report, base_ref_resolvable, compute_changed_lines,
render_changed_block.

src/frob/tickets/__init__.py: 2333 -> ~1250 lines (well below the <2000
acceptance target). _land.py (4866 lines) was NOT touched this dispatch --
requeued as residue, see below (follow-up filed and landed as T-1171).

_load_ticket_and_queue and _load_one stay in __init__.py (both are shared by
non-evidence families still there -- mutate_labels, add_acceptance,
new_ticket's late-import of _check_evidence_resolution/
_validate_evidence_list). The new module late-imports these plus
_OPEN_STATES, _TRANSITIONS, validate_evidence, and _validate_evidence_list
from the package at call time, matching _setters.py/_scope.py's own
load-order-safe indirection for the identical reason (__init__ imports
_evidence.py before any of these names exist at its own module scope).

Two monkeypatch-indirection hazards found by running the full affected test
suite before committing (not by inspection alone):
1. tests/test_tickets_cmd_evidence.py::TestAddCmdEvidenceLoadAndWriteFailures
   ::test_write_failure_propagates monkeypatches the PACKAGE attribute
   `frob.tickets.write_ticket` -- the three call sites inside _evidence.py
   (transition, _append_evidence_and_write, replay_evidence_from_done_report)
   now late-import write_ticket from the package instead of a module-top
   binding from _store, so the patch still takes effect.
2. tests/test_tickets_cmd_evidence.py::TestRunCmdEvidenceLaunchFailure
   monkeypatches `frob.tickets.subprocess.run` -- re-added a bare
   `import subprocess` to __init__.py itself (subprocess is one shared
   module object process-wide, so this binding only needs to exist at the
   package's own top level for the patch to reach _evidence.py's
   `guarded_subprocess_run` call).

INV006: the moved `transition` function carried this file's only
frob:invariant INV-002 anchor -- __init__.py's remaining exclusivity ("only")
claims were left unanchored, so added a file-level frob:waive INV006 to
__init__.py, same T-0585 calibration-batch disposition as every sibling
split module. Also added the file-level ARCH102 waiver _evidence.py itself
needs (26 exports/4 naming clusters, same single-concern rationale as
__init__.py's own long-standing ARCH102 waiver).

DUP001: the moved _check_cmd_evidence_kind tripped a fresh 95%-similarity
pairing against several unrelated tiny allowlist-guard functions elsewhere
in the repo (file-identity is part of the dup pairing key, so a move alone
can surface a new pairing even with byte-identical code) -- waived with the
same T-0861 DEBT001/DEPR001/TEST010 false-positive-class disposition.

SELFAUDIT001/design/frob.strata: replay_evidence_from_done_report was a
pre-existing gap in the interface= attrs list for the tickets_ledger store
node (present in __all__-adjacent exports but never added to the strata
design file) -- added it. Also added it to __all__ itself (also a
pre-existing gap). `frob sys sync-interface --check`: no drift.

docs/modules/tickets.md and 3 test files (test_tickets.py,
test_tickets_cmd_evidence.py, test_tickets_tiers.py) had frob:describes /
frob:tests directives re-pointed from src/frob/tickets/__init__.py to
src/frob/tickets/_evidence.py for every moved symbol; added frob:ticket
T-1152 edges to the touched test classes/methods (COV002); extended the
ticket's scope to include test_tickets_cmd_evidence.py, test_tickets_tiers.py,
and design/frob.strata (the ticket's own plan requires touching whichever
tests/*.py files carry directives for a moved symbol, and the strata fix was
a direct SELFAUDIT001 consequence of the split).

Mid-dispatch: main advanced substantially (several other tickets landed
concurrently in this parallel-drive wave) while this dispatch was in
progress -- caught via the exact playbook 1/9 hazard class (a freshly
unexpected strata-core .rs diff during an unrelated gate run), committed
WIP, merged main (one real conflict in __init__.py's _models import block,
resolved by keeping the post-split import list since main's own concurrent
cleanup commit (7925f51a) had already independently removed several of the
same now-unused imports I was removing), rebuilt natives, and re-ran the
full gate/test suite fresh against the merged tree.

_land.py's own split (preflight/merge-splice/verify/sweep families, T-1108's
original plan) was NOT attempted this dispatch -- filed as residue,
real id assigned at land-time renumber.

Gates: `frob check --ticket T-1152` clean across gates-native, gates-security,
test, and the full drift/coverage/invariant/policy/... --only chunk list
(zero errors in every group after the fixes above; remaining findings in
every group are pre-existing/unrelated, verified against main baseline).
`frob sys sync-interface --check`: no drift. `frob test --base main`: 41
outcomes, exit 0.

### Changed
```
 design/frob.strata                 |    1 +
 docs/modules/tickets.md            |   22 +-
 src/frob/tickets/__init__.py       | 1141 ++--------------------------------
 src/frob/tickets/_evidence.py      | 1193 ++++++++++++++++++++++++++++++++++++
 tests/test_tickets.py              |   12 +-
 tests/test_tickets_cmd_evidence.py |   41 +-
 tests/test_tickets_tiers.py        |   14 +-
 tickets.md                         |   27 +-
 8 files changed, 1312 insertions(+), 1139 deletions(-)
```

### Evidence
- `tests/test_evidence_integrity.py::TestD10CmdEvidenceReverify::test_reverify_true_when_command_still_reproduces` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_allows_when_evidence_reverified_true` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_permissive_when_evidence_reverified_none` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_rejects_when_evidence_reverified_false` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_allows_when_mutation_evidence_true` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_permissive_when_mutation_evidence_none` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_rejects_when_mutation_evidence_false` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_fails_loudly_on_now_failing_evidence` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_passes_on_strengthened_done_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_refuses_non_done_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidence::test_resolvable_ids_appended` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidenceValidation::test_add_evidence_appends_and_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidenceValidation::test_add_evidence_normalizes_dot_form_before_resolving_and_storing` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStateMachine::test_legal_transitions` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStateMachine::test_transition_queued_to_planned_unit` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestAddCmdEvidenceLoadAndWriteFailures::test_ticket_not_found_propagates_load_error` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestAddCmdEvidenceLoadAndWriteFailures::test_write_failure_propagates` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_exit_zero` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_nonzero_exit` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestKindGate::test_bug_kind_rejected` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestKindGate::test_docs_kind_closes` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestRunCmdEvidenceLaunchFailure::test_oserror_on_launch_is_evidence_cmd_failed` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_epic_close_allowed_once_descendant_done` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_epic_close_refused_with_open_descendant` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_plain_ticket_close_unaffected_by_guard` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 26 passed (from 26 evidence id(s))
- gates: 0 error(s), 960 warning(s), 505 waived
- error-findings: none (measured, zero errors)
