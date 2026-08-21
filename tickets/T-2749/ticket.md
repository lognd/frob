---
id: T-2749
title: 'post-land sweep regression from T-2738: 2 new (rule, file) identit(ies), 7
  finding(s) (ARCH103, DRIFT002)'
state: done
kind: bug
origin: agent
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/tickets/_land.py
evidence_scope:
- tests/unit/test_close_promote_drafts.py
- tests/unit/test_land_already_landed.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: carry the coordinator's two-question measurement and the genuine-regression
    distinction onto the surviving auto-filed ticket before dropping the duplicate
  actor: logan
  at: '2026-08-20'
  old_length: 1901
  new_length: 4042
- mode: append
  reason: T-2749 remedy is shape-only (function split + directive-string fix), BUG002
    confirmatory-only guard does not apply
  actor: logan
  at: '2026-08-20'
  old_length: 4042
  new_length: 4812
evidence:
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_with_no_drafts_is_unchanged
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_reports_and_exits_nonzero_when_a_draft_cannot_be_promoted
- tests/unit/test_land_already_landed.py::TestAlreadyLandedStaleRapidDebtDirt::test_stale_rapid_debt_dirt_does_not_block_already_landed_detection
- tests/unit/test_land_already_landed.py::TestAlreadyLandedStaleRapidDebtDirt::test_genuine_uncommitted_code_change_still_defers_even_with_stale_rapid_debt_dirt
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2738 at commit b864a1074d3e74064cd98a0e3322b27064cedbf9 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 7 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH103  src/frob/app/ticket_runner/_close_cmd.py
- DRIFT002  src/frob/tickets/_land.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH103  src/frob/app/ticket_runner/_close_cmd.py  -> attributed to T-2738 (commit b864a1074d3e, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_close_cmd.py::_close -> src/frob/app/ticket_runner/_close_cmd.py::_close_failure_hint -> src/frob/app/ticket_runner/_close_cmd.py::_hint_invalid_transition
- DRIFT002  src/frob/tickets/_land.py  -> attributed to T-2738 (commit b864a1074d3e, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_close_cmd.py::_close -> src/frob/app/ticket_runner/_close_cmd.py::_close_guards_for_ticket -> src/frob/app/ticket_runner/_close_cmd.py::_close_mutation_evidence_for_ticket -> src/frob/tickets/_land.py::_must_still_pass_land_violations -> src/frob/tickets/_land.py::_must_still_pass_waiver_reason -> src/frob/tickets/_land.py::_BUG003_WAIVER_RE

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.



## COORDINATOR ANALYSIS: these are GENUINE regressions, unlike most sweep tickets here

Both findings pass BOTH tests, measured before this ticket was auto-filed:

Q1 -- do they reproduce on current main? YES, both at ERROR severity,
via `frob check --json --no-cache`.

Q2 -- did the blamed land touch the files? YES:

    git show --stat b864a1074
      src/frob/app/ticket_runner/_close_cmd.py | 84 ++++++++++++++
      src/frob/tickets/_land.py                | 55 ++++++++++-

Both carry a real commit_sha (b864a1074) and ticket_id (T-2738), so the
attribution engine connected them correctly.

## Do not treat this as more of the same

Most quarantine batches this session were PRE-EXISTING debt surfaced by
the repaired deferred verification (T-2713/T-2715), carrying null
commit_sha against files the blamed land never touched -- detection
events, not regressions. T-2732 was 137 findings of which 136 were
already-waived note-severity sites and exactly one was live.

This is the opposite case: attributed, reproducing, error-severity, in
files the land demonstrably rewrote. It is real work.

## Fix direction

ARCH103 and DRIFT002 are structural rules about the shape of the added
code, not about whether T-2738's feature works, so this should not
require revisiting its design. Read T-2738's diff first -- the right
remedy is almost certainly bringing the new code into line with the rules
rather than waiving them. If either turns out to be a false positive of
the rule, that is a legitimate outcome, but state the measurement and fix
the rule.

## Positive controls, both directions

- both findings stop reproducing under `frob check --no-cache` after the fix
- ARCH103 and DRIFT002 STILL fire on a planted genuine violation of each,
  as real fixtures -- a narrowing that silences a rule is a regression,
  and this repo has shipped that mistake before
- T-2738's own behavior is unchanged: closing a ticket still promotes its
  pending drafts, and its tests still pass

Supersedes T-2750, which I filed for this identical finding pair moments
before the rapid sweep auto-filed this one; T-2750 is dropped as a
duplicate.

frob:no-behavior-change reason="both remedies here are shape-only: the ARCH103 fix splits _promote_pending_drafts_after_close into three smaller private helpers with identical control flow (measured: all 3 test_close_promote_drafts.py tests pass unchanged before and after), and the DRIFT002 fix corrects two frob:tests directive strings to point at the class the tests actually live in (TestAlreadyLandedStaleRapidDebtDirt, not TestAlreadyLandedOnMain) -- no production code in _land.py changed at all. Neither remedy changes runtime behavior, so BUG002's confirmatory-only guard is expected to fire; verified instead via measured before/after frob check --no-cache reproduction (see Done report) and planted-fixture positive controls for both ARCH103 and DRIFT002."