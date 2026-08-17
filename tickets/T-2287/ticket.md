---
id: T-2287
title: unlanded-branch detector greps blob text, so fixture frob:ticket strings in
  3 test files make 239 of 244 findings false positives
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_unlanded.py
- tests/unit/test_unlanded_branch_work.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given the repo as of 2026-08-17, when frob ticket reconcile runs, then the
    unlanded-work report contains the five genuine findings and none of T-9001/T-0104/T-1/T-draft-9bda8d62
  evidence: []
- text: given a test file containing a fixture frob:ticket T-9001 string literal,
    when the directive-anchored signal scans it, then no finding is emitted
  evidence: []
- text: given a genuine directive-anchored specimen (committed non-tickets file with
    a live frob:ticket directive and a non-in-progress ticket.md), when the signal
    scans it, then the finding is still emitted
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17: `frob ticket reconcile` reports 244 unlanded-work
findings across 117 branches. Exactly 5 are real (T-1860@t-1860,
T-2131@t-2131, T-1238@t-2097, T-1238@t1539-series,
T-1238@worktree-agent-a813bca499a672a7b). The other ~239 are the fixture
ids T-9001, T-0104, T-1 and the draft id T-draft-9bda8d62, repeated once
per branch. A 98% false-positive rate makes the alarm unreadable, so the
five genuine leaks -- the exact failure class T-1934 exists to catch --
are invisible in the noise.

ROOT CAUSE: T-1948's `directive-anchored` signal in
`src/frob/tickets/_unlanded.py` greps blob TEXT with
`_TICKET_DIRECTIVE_RE = re.compile(r"frob:ticket\s+(T-[0-9A-Za-z][0-9A-Za-z-]*)")`
over every changed non-`tickets/**` file. The module's own docstring states
it "never parses source, only greps blob text". Three test files carry
literal `frob:ticket T-####` strings as FIXTURE DATA, not as live
directives:

  tests/test_gates.py            (1 hit)
  tests/test_gates_fix_engine.py (5 hits)
  tests/test_graph.py            (2 hits)

Those fixture ids have no `ticket.md` on the branch at all, so the
disagreement check ("anything other than in-progress, including missing
entirely") fires for every branch that touches any of those three files --
which is nearly every branch in the repo.

This is the standing "token/grammar fixes, never lexical" rule: a
substring match is wrong in both directions. It matches fixture strings and
commented-out mentions, and it would miss a directive written through an
alias.

FIX DIRECTION (implementer to confirm): the directive signal must
distinguish a real directive site from fixture text. Options, cheapest
first -- (a) reuse the repo's existing directive PARSER (the one
`frob.graph` uses for the comment DSL) instead of a bare regex, so a
string literal inside test source is not a directive site; (b) at minimum,
require the matched id to RESOLVE to a real ticket (present on the branch
or on main, active or archived) before reporting -- an id no ref knows
about is fixture data, not a leak. Note (b) alone is a narrowing
heuristic, not a parse, and will still match a commented-out real id.

POSITIVE CONTROL REQUIRED: the fix must (1) still report all five genuine
findings listed above, and (2) drop the fixture ids. A regression test
must plant a fixture-style `frob:ticket T-9001` string in a test-shaped
file AND a genuine directive-anchored specimen, and assert the detector
separates them. A "clean" verdict with no must-fail fixture proves
nothing.
