---
id: T-3156
title: D-02 has no legitimate evidence route for docs-only bug-kind or Rust-only tickets
state: done
kind: bug
origin: human
created: '2026-08-27'
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_evidence_integrity.py::TestD02ScopeBinding::test_evidence_covers_scope_true_for_bug_kind_with_no_python_surface
- tests/test_evidence_integrity.py::TestD02ScopeBinding::test_evidence_covers_scope_false_for_bug_kind_with_real_python_surface
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_bug_kind_with_no_python_surface_scope_closes
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_bug_kind_with_real_python_surface_scope_still_rejected
- tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose::test_land_validate_closeable_accepts_bug_kind_no_python_scope
- tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose::test_land_validate_closeable_refuses_bug_kind_real_python_scope
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 21055ca26f9b39b46b2f04c18961011be27934f5
---
## Description
Found while auditing T-3147 (D-02 self-cover tautology blast radius,
2026-08-10..2026-08-27 window). D-02 (evidence_covers_scope) has exactly
two legitimate routes: a real TESTS graph edge, or the evidence file's
own presence in ticket.scope. Neither route accommodates two recurring,
otherwise-legitimate shapes of work, both of which relied on the now-
removed evidence_scope auto-widen (T-1944/T-3141) to close at all:

1. Rust-only (strata-core) tickets with no PyO3 surface of their own
   (T-3005, T-3007 precedent): the real evidence is `cargo test`, which
   frob has no channel to bind or verify at all -- so a done-report
   narrates the cargo run in prose and the ticket record binds an
   unrelated pytest smoke id (test_parse.py) just to have SOMETHING
   D-02 can see. Confirmed disclosed and honest in both cases, but
   structurally the ticket record cannot prove what the prose claims.

2. `docs`/`ux`-kind tickets get a `cmd:` evidence channel (T-0215) for
   "no pytest surface of its own" closes. A `bug`-kind ticket whose
   actual resolution is docs/ledger-only (an investigation, a stale-
   baseline correction, a phantom-draft note-rewrite -- this audit
   found 6: T-2804, T-2893, T-2902, T-2946, T-2955, T-3060) has NO
   legitimate route at all: not `cmd:` (wrong kind), not a TESTS edge
   (no code), not `demote_to_evidence_only` (requires the glob to have
   been in `scope` first, which an arbitrary smoke test never was).
   These closed only because the tautology waved them through; post-
   T-3141 they have no honest way to close without either a scope-widen
   they don't need or a kind change that misrepresents the ticket.

## Plan
Design one additional legitimate D-02 route for these two shapes --
likely: extend `CMD_EVIDENCE_ALLOWED_KINDS` reasoning to cover a
`bug`/`feature` ticket whose entire scope is non-code (docs/ticket
files only, mirroring the existing docs/ux carve-out) and/or a native-
test attestation channel for `cargo test` output analogous to `cmd:`
evidence, scoped to `strata-core/**`. Do not just re-add T-1944's old
auto-widen (that is the exact tautology T-3141 removed) -- any new
route must require an explicit, reasoned signal at record time, same
posture as `demote_to_evidence_only`'s `--reason`.

## Evidence audit trail (T-3147)
Of 18 DONE tickets (all landed 2026-08-25..2026-08-27, inside the
T-1944/T-3141 window) whose evidence_scope carried a path that was
never a real `scope`-to-`evidence_scope` demotion and would fail a
scope-only D-02 recheck:
- 4 (T-2645, T-2914, T-2970, T-3093) independently REACH per
  `classify_evidence_reach` (T-3046) -- tautology was harmless, evidence
  is genuinely related, just not formally scoped.
- 2 (T-2956, T-3064) classify DOES_NOT_REACH but are independently
  exempt/resolved: T-2956 is a disclosed `frob:no-behavior-change`
  waiver triage; T-3064 was explicitly left closed by T-3087's own
  disposition (superseded by T-3086).
- 3 (T-3005, T-3007, T-3056) are strata-core (Rust) tickets -- reach
  classifier reports UNKNOWN (no cross-language call graph). Verified
  by direct done-report inspection: real `cargo test` evidence is
  documented in prose in all three; not laundered, just unverifiable by
  frob today. This is finding (1) above.
- 9 (T-2384, T-2804, T-2892, T-2893, T-2902, T-2909, T-2946, T-2955,
  T-3060) are docs/ledger-only tickets under the repo's own playbook
  sec-5 "no pytest surface of its own" convention. Verified by done-
  report inspection: real work is the scope-declared doc/ticket diff
  itself; the bound pytest id is a acknowledged placeholder smoke test,
  not a laundering attempt. 6 of the 9 are `bug`-kind, which is finding
  (2) above.

No ticket in the audited population needs reopening or re-evidencing --
all 18 are fine on inspection, by one of the two independent checks or
by direct done-report verification. This ticket is the FORWARD gap the
audit exposed, not a retroactive fix.