---
id: T-4019
title: 'F-232: one malformed invariants/*.md aborts ALL gate loading and the run reports
  ''skipped ... pass'' -- whole-repo enforcement silently off'
state: in-progress
kind: bug
origin: human
created: '2026-09-06'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/invariants.py
- src/frob/gates/__init__.py
- tests/gates_suite/test_invariant.py
- docs/modules/gates.md
- src/frob/check/_python.py
- tests/unit/test_check.py
- tests/gates_suite/test_run.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: abort-as-pass and blast-radius fix require touching _load_required_state/_load_graph_queue_lock
    in gates/__init__.py; ticket body directs this file explicitly
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/gates_suite/test_invariant.py
  reason: load_invariants signature changes (per-file scoping, no-longer-aborts-whole-run)
    require rewriting its unit tests, and the fixtures proving the fix live in test_gates.py's
    run_gates integration tests
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/gates_suite/test_gates.py
  reason: load_invariants signature changes (per-file scoping, no-longer-aborts-whole-run)
    require rewriting its unit tests, and the fixtures proving the fix live in test_gates.py's
    run_gates integration tests
  actor: logan
  at: '2026-09-06'
- op: add
  glob: docs/modules/gates.md
  reason: Invariants section documents load_invariants' abort-on-first-malformed-file
    contract, which this fix changes to per-file scoping
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/check/_python.py
  reason: '_gates_error_result is the literal place a run_gates Err(ConfigMalformed)
    is rendered: exit_code=0 summary=''gates skipped: ...'' -- defect 1 (abort prints
    as pass) is fixed here, not just in gates/__init__.py'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_check.py
  reason: existing _gates_error_result coverage (TestGatesErrorResultQueueUnavailable
    et al) and the new must-not-print-pass-for-unexecuted-stage fixture live here
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/gates_suite/test_gates.py
  reason: test_gates.py does not exist in this repo; the real run_gates integration
    suite (where the must-fire/must-stay-quiet fixtures belong) is test_run.py
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/gates_suite/test_run.py
  reason: test_gates.py does not exist in this repo; the real run_gates integration
    suite (where the must-fire/must-stay-quiet fixtures belong) is test_run.py
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/gates/_waive.py
  reason: the two new rule ids this fix introduces (INV009, GATES001) must be registered
    in _KNOWN_GATE_RULES or GATERULE001 flags them as unregistered
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
ONE MALFORMED FILE TURNS OFF EVERY GATE, AND THE RESULT REPORTS AS PASS. This is
the largest-blast-radius silent zero found in this drive.

Consumer logand.app-v2 F-232, 2026-09-06, MEASURED by them on T-0188: an
invariants/*.md file with id INV-ADMIN-DATA-001 makes "every gate report
'skipped ... pass', not just gate:INV".

VERIFIED END TO END IN OUR SOURCE:

  1. src/frob/gates/invariants.py:27   _ID_RE = re.compile(r"^INV-\d{3}$")
     so a descriptive id like INV-ADMIN-DATA-001 fails validation.
  2. invariants.py:229-231             returns Err(InvariantError.Malformed)
     for that ONE file.
  3. src/frob/gates/__init__.py:6488   _require(load_invariants(root),
                                       "invariants load",
                                       GateError.ConfigMalformed)
     and :6491 `return Err(...)` -- so _load_gate_state, which loads graph,
     queue, lock, invariants AND policy for the WHOLE run, aborts.

THREE SEPARATE DEFECTS, IN DESCENDING SEVERITY:

1. THE BLAST RADIUS IS WRONG. A single unparseable invariant file disables every
   gate in the run. The correct scope of a malformed-file failure is THAT FILE's
   invariant, not the entire gate stage. Every other gate -- SEC, PII, COV, SCOPE
   -- has nothing to do with invariant frontmatter and should still run.

2. THE FAILURE RENDERS AS SUCCESS. This is the part that makes it dangerous
   rather than merely annoying. A hard config error is reported as "skipped ...
   pass", so a repo can sit indefinitely with ALL ENFORCEMENT OFF while CI stays
   green. It is the infrastructure-failure-as-semantic-verdict class (five prior
   instances: a killed child read as "unmeasurable", collection exit 2 read as
   "evidence gone", a malformed ledger read as "ticket not found", a merge
   conflict read as "evidence did not pass") in its most consequential form: the
   verdict is not about one ticket, it is about the entire repository.
   A skipped gate MUST NOT print as pass. If it cannot run, that is an error.

3. THE TWO ID GRAMMARS DISAGREE. The consumer notes the code directive
   (frob:invariant) accepts the descriptive id their T-0170 uses, while the file
   loader demands ^INV-\d{3}$. One concept, two spellings, and the mismatch is
   only discovered by the whole gate stage silently switching off. They also
   argue descriptive ids are more useful than three digits, and they are right --
   INV-ADMIN-DATA-001 says what it protects; INV-007 does not. Widening the
   loader's grammar to match the directive's is the fix; do NOT narrow the
   directive instead, that would break working code to satisfy a regex.

WHY WE COULD NEVER HAVE FOUND THIS OURSELVES, which is worth recording: this
repo's own invariants/ directory is EMPTY, and that is already documented on
T-3928 as a defect in its own right ("invariants/ is therefore EMPTY AND THE
INVARIANT GATE PASSES VACUOUSLY ON EVERY RUN"). A repo with no invariant files
cannot have a malformed one. Same structural blindness that hid the
hyphenated-scaffold and hardcoded-src/frob defects -- we are systematically
unable to see defects in features we do not use.

STRONG CROSS-REFERENCE: T-3985's subject-count primitive would surface defect 2
immediately -- a gate reporting a verdict over zero subjects because it never ran
is exactly what that primitive makes impossible to state silently. Sequence
accordingly and say in the Done report whether T-3985 subsumes any of this.

MUST-FIRE FIXTURE: a malformed invariant file produces an ERROR naming that file,
and a non-zero exit.
MUST-STAY-QUIET: every OTHER gate still runs and reports normally in the presence
of one malformed invariant file.
THIRD FIXTURE: a descriptive id accepted by the frob:invariant directive is also
accepted by the file loader -- the grammars agree.
FOURTH FIXTURE: no gate ever prints "pass" for a stage that did not execute.

ACCEPTANCE
- Malformed-file failure scoped to that file, not the run.
- A skipped/aborted gate never reports pass; exit status reflects it.
- One id grammar shared by the directive and the loader, widened not narrowed.
- All four fixtures committed.