---
id: T-2656
title: Fix 13 stale lease/binding-premise waivers surfaced by WAIVE006's T-2622 extension
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_decisions_compliance.py
- src/frob/gates/_doclink_docanchor.py
- src/frob/gates/_sys.py
- src/frob/gates/_tickets_gate.py
- src/frob/gates/_todo_fmt.py
- src/frob/gates/_coverage.py
- src/frob/gates/_mutation_evidence.py
- src/frob/tickets/_evidence.py
- src/frob/tickets/_models.py
- src/frob/tickets/_draft_finalize.py
evidence_scope:
- tests/test_waive_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
- tests/test_waive_gate.py::TestWaive007RealRepo::test_zero_findings_on_real_repo
designated_repro_test: tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 68cb346e98027a98976ddfdf09ced0f405f865eb
---
## Description

T-2622 extended WAIVE006/007's binding-phrase extraction
(`_WAIVE006_BINDING_PHRASE_RES` in `src/frob/gates/_waive_comments.py`)
to recognize "T-#### holds/holding/under a live lease" style premise
phrasing, not just "pending T-####"/"blocked on T-####". Running the
extended check against this repo's OWN current tree (not a fixture)
surfaced 13 genuinely stale waiver sites -- the cited ticket really has
gone DONE, and nobody re-reviewed the waiver, exactly the T-2612 class
this whole family of work exists to close. These 13 sites are OUTSIDE
T-2622's declared scope (`src/frob/gates/_waive.py`,
`src/frob/gates/_waive_comments.py`, `tests/test_waive_gate.py`) and are
not fixed by that ticket -- filed here instead, per playbook: fix what's
in scope, file what's not, never fold it in silently.

Each site's waiver reason claims a specific ticket "holds/holding a
lease" as the reason a file/site is (or was) out of formal scope; every
cited ticket below is now DONE, so the premise no longer holds. Fix each
by either (a) confirming the underlying constraint the waiver names is
genuinely resolved and removing the waiver, or (b) if the site still
needs a waiver for an unrelated/still-live reason, reword it the way
`src/frob/gates/_waive.py`'s own top-of-file SCOPE001 waiver was reworded
by T-2622 (past tense, non-binding historical narration, current
justification stated explicitly) -- see that file's own top comment for
the worked example.

### SCOPE001 sites bound to T-1279 (DONE, TEST005 burn-down) -- 6 sites,
same copy-pasted waiver pattern across `src/frob/gates/**`:
- `src/frob/gates/__init__.py`
- `src/frob/gates/_decisions_compliance.py`
- `src/frob/gates/_doclink_docanchor.py`
- `src/frob/gates/_sys.py`
- `src/frob/gates/_tickets_gate.py`
- `src/frob/gates/_todo_fmt.py`

### AFFECT001 sites bound to T-1235 (DONE) -- 2 sites:
- `src/frob/gates/_coverage.py::load_coverage`
- `src/frob/gates/_coverage.py::write_coverage_lock`

### AFFECT001 sites bound to T-1739 (DONE) -- 4 sites:
- `src/frob/gates/_mutation_evidence.py::mutation_evidence_violations`
- `src/frob/tickets/_evidence.py::replace_evidence`
- `src/frob/tickets/_models.py::Ticket`
- `src/frob/tickets/_models.py::TicketError`

### AFFECT001 site bound to T-2076 (DONE) -- 1 site:
- `src/frob/tickets/_draft_finalize.py::finalize_draft`

## Plan

For each site: read the waiver's full reason, check whether the doc/
scope work it deferred was actually done since the cited ticket closed
(most likely, per T-2612's own audit finding "9 of 12 still owed real
work" -- do not assume "premise expired" means "safe to delete", per
T-2612's own explicit instruction). Fix or reword accordingly. Re-run
`TestWaive006RealRepo`/`TestWaive007RealRepo` in
`tests/test_waive_gate.py` (which encode this exact known-debt allowlist,
keyed to this ticket's id -- shrink the allowlist as each site clears,
remove it entirely once this ticket closes).

## Acceptance

- [0] given the 13 sites above, when re-reviewed, then each either has
      its stale waiver removed/re-justified, or a real follow-up ticket
      is filed for genuinely-owed doc/scope work the original waiver
      deferred (T-2612's own posture: expired premise != dead finding).
- [1] `tests/test_waive_gate.py::TestWaive006RealRepo`/`TestWaive007RealRepo`
      pass with the known-debt allowlist for this ticket's id fully
      removed (not just shrunk).