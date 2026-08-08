## Done report

TICK002 already auto-fixes a `T-draft-*` id that survived onto main by
renumbering it (`finalize_draft` -> `renumber_one`), because a real
ticket exists for that primitive to act on. TICK006's phantom case is
harder and was the actual gap this ticket closes: the cited id resolves
to NO block anywhere -- active ledger or archive -- so there is nothing
for `renumber_one` to rename FROM.

`fix_tick006_phantom_refile` (new Tier-A handler, `src/frob/gates/
_fix_engine.py`) does what TICK006's own finding message tells the
operator to do:
1. Scans every ticket's Done report for a phantom filing claim
   (`frob.gates._tickets_gate._tick006_phantom_ids`, the same detector
   TICK006 itself uses).
2. Files a REAL ticket for each phantom id via `new_ticket`, quoting the
   original claim's own surrounding ~300-char text verbatim in the new
   ticket's body -- the only surviving description of whatever work the
   phantom id was meant to cover, since the ticket itself never existed
   to describe it directly. Filed `kind=bug, priority=high`: a phantom
   filing trail is itself the T-0707/T-0615 incident class, not ordinary
   follow-up work.
3. Rewrites the phantom citation in the CLAIMING ticket's own body to
   the new real id, reusing `frob.tickets._new_renumber.
   _rewrite_body_prose_references` -- the exact same whole-word
   prose-citation rewrite `renumber_one`/T-1125 already use for a
   genuine renumber, not a second, independently-drifting
   implementation of the same substitution.

A no-op whenever `new_ticket` itself fails (logged, never silent) --
the phantom citation is left exactly as TICK006 already reports it
rather than being rewritten to an id that was never actually filed,
which would just manufacture a second phantom.

Wired into `TIER_A_HANDLERS["TICK006"]` alongside TICK002 (both touch
the ledger, both run before WAIVE004 per the existing ordering
discipline).

Split into three functions (`fix_tick006_phantom_refile` /
`_tick006_refile_for_ticket` / `_tick006_refile_ticket_spec`) to stay
under ARCH001's 60-line threshold -- pure extraction, no behavior
change from the original single-function draft.

An earlier version of this Done report disclosed two unrelated
`_resolve_ticket_root` findings (ARCH103/SEC110, from the already-landed
T-1674) as out-of-scope and filed a follow-up for them -- by the time
this round's `frob check --ticket T-1544` ran clean, another concurrent
agent had already split/fixed that function, so the follow-up draft was
not refiled after this ticket's mid-session worktree reset (T-1720's
own recipe: reset to main's tip, reapply this ticket's own diff, and
re-verify from a clean base rather than carrying stale findings
forward).

### Changed
```
 design/frob.strata            |   4 +-
 docs/modules/gates.md         |  15 ++++
 src/frob/gates/_fix_engine.py | 161 +++++++++++++++++++++++++++++++++++++++++-
 tests/test_gates.py           | 112 +++++++++++++++++++++++++++++
 tickets/T-1544/ticket.md      |  30 +++++++-
 5 files changed, 316 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_tick006_refiles_and_rewrites_citation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_tick006_known_id_is_never_touched` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 1559 warning(s), 728 waived
- error-findings: PRE001@tickets/T-1544, SELFAUDIT001@design
