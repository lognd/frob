---
id: T-3416
title: Update design/frob.strata SYS100 fs.read capability for process/_reap split
  (T-3396)
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record the four failing tests this and T-3409 jointly cause, plus the split-loses-capability-declarations
    pattern seen three times today
  actor: logan
  at: '2026-08-29'
  old_length: 1946
  new_length: 5111
- mode: append
  reason: 'BUG002 waiver: fix is a declaratory design-model correction, one of two
    companion fixes needed to turn the four SYS100 tests green'
  actor: logan
  at: '2026-08-29'
  old_length: 5111
  new_length: 6242
evidence:
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbolsCorpusWide::test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations`
fails on main independent of T-3350/T-3413's nodeid.py regression (measured after
T-3413's fix was applied but not yet landed, caches cleared, no REPLAY):

  SELFAUDIT001 (SYS100, node=core): fs.read observed but not declared
      src/frob/process/_proc_scan.py:82
      src/frob/process/_proc_scan.py:134
      src/frob/process/_proc_scan.py:186
      src/frob/process/_proc_scan.py:227
      src/frob/process/_proc_scan.py:403

A sixth, closely related finding for src/frob/stats/_agentic_shared.py:42 is
ALREADY tracked at T-3409 (queued) -- do not duplicate that one here, only
the src/frob/process/_proc_scan.py side is new.

src/frob/process/_proc_scan.py traces to T-3396 (already closed/landed),
which split src/frob/process/_reap.py under LARGE001's 800-line threshold
and produced _proc_scan.py as a sibling module. Same shape as T-3409 and as
T-3350/T-3413's own root cause: a module split moved fs.read-performing code
into a new file whose design-model capability declaration (`may "fs.read"
via ...` on the `core` node) was never updated to include it.

Filed separately from T-3413 because it predates T-3350 and is caused by a
different, unrelated ticket (T-3396) -- not a T-3350 regression.
`tickets/T-3388/ticket.md`'s `frob:waive BUG002 ... follow_up="T-3413"`
clause names `test_sys_gate_zero_violations` as confounded specifically by
T-3350's regression; T-3413 fixes that half, but THIS ticket (plus T-3409)
is the other half still keeping that test red, so T-3388's waiver should
not be cleared until both are fixed.

Fix direction: add `src/frob/process/_proc_scan.py` to `core`'s
`may "fs.read" via ...` declaration in design/frob.strata (mirroring the
existing declaration for its sibling files in the same node), then
re-measure `test_sys_gate_zero_violations` clean (together with T-3409's
fix for the _agentic_shared.py side).


BLAST RADIUS MEASURED, 2026-08-29. These six undeclared `fs.read` sites are not
gate-only noise: together with T-3409's single site they fail FOUR tests across
two suites. Whoever fixes this should bind these as evidence rather than
inventing a new test.

MEASURED on a quiet box (load near zero, no concurrent worktree mutation, no
coverage instrumentation), xdist -n 8:

  tests/unit    collected=5908  failed=9
  tests/system  collected=447   failed=3   (serial)

Of those twelve failures, FOUR trace to this one root cause:

  tests/unit/strata/test_selfconform.py::TestRealGateGreen
      ::test_repo_design_and_declarations_are_self_conformant
  tests/unit/strata/test_selfconform.py::TestCoverageTotality
      ::test_repo_unrestricted_scan_is_clean
  tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch
      ::test_real_repo_design_selfconform_has_no_eval_gap
  tests/system/test_frob_self_model.py::TestFrobSelfModel
      ::test_sys_gate_zero_violations

The first one's failure output names the violations exactly:

    AssertionError: [('SYS100', 'core', "capability 'fs.read' observed at
    src/frob/process/_proc_scan.py:82 but not declared"), ... ,
    ('SYS100', 'core', "capability 'fs.read' observed at
    src/frob/stats/_agentic_shared.py:42 but not declared")]
    Left contains 6 more items

Five sites are in `src/frob/process/_proc_scan.py` (lines 82, 134, 186, 227,
403) and belong to THIS ticket. The sixth, `src/frob/stats/_agentic_shared.py`
line 42, belongs to T-3409. Neither ticket alone turns these tests green -- both
must land. Coordinate, or land them together.

PROVENANCE, so nobody re-derives it: both files are NEW, created by splits that
landed 2026-08-29. `_proc_scan.py` came out of T-3396's split of
`src/frob/process/_reap.py`; `_agentic_shared.py` came out of T-3059's split of
`src/frob/stats/_agentic.py`. Both splits were correct and both cleared their
LARGE001 debt. What neither did was carry the moved code's CAPABILITY
DECLARATIONS across into the design model -- the `fs.read` calls existed before
the split and were declared against their old home.

THAT IS THE PATTERN WORTH NOTICING, and it is the third instance today: T-3350's
split of `symref_to_nodeid` into `src/frob/nodeid.py` produced the same class of
failure (SYS003/SYS102, tracked and fixed under T-3413). Three splits, three
design-model gaps. A file split is a design-model change, and nothing currently
reminds anyone of that at split time. Consider whether that deserves its own
ticket -- a check that a newly-added source file is covered by some node's
`code=` glob would have caught all three at land time. Do not build it under
this ticket; say whether it is worth building.

EVIDENCE GUIDANCE: bind the four tests above. They fail now and will pass once
both halves land, which is a genuine fail-then-pass repro rather than a
confirmatory-only one. Run `frob ticket evidence --check-repro` to confirm.

DO NOT declare `fs.read` on a broader node or widen an existing glob just to
silence SYS100. The declaration should describe what the code actually does, at
the granularity the model already uses for its siblings.


frob:waive BUG002 reason="this ticket adds five src/frob/process/_proc_scan.py sites to core's existing may fs.read via declaration in design/frob.strata -- a declaratory design-model correction, not a code-behavior defect with its own fail-then-pass unit test. The four tests that DO fail-then-pass on the full fix (test_repo_design_and_declarations_are_self_conformant, test_repo_unrestricted_scan_is_clean, test_real_repo_design_selfconform_has_no_eval_gap, test_sys_gate_zero_violations) require BOTH this ticket and T-3409 (the src/frob/stats/_agentic_shared.py sixth site) landed together -- confirmed by direct re-run: after this fix alone, test_repo_design_and_declarations_are_self_conformant's violation list drops from 6 items to exactly the 1 remaining T-3409 item (src/frob/stats/_agentic_shared.py:42), so this fix cannot independently turn any of the four tests green. test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count (bound as evidence) parses the real design/frob.strata this change edits and passes cleanly against the real repo, guarding against a malformed edit." follow_up="T-3409"
