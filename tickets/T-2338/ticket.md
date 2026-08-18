---
id: T-2338
title: PERF008 waiver reason display can be misattributed between two same-rule waivers
  in one file
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_waive.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_match_waiver_picks_line_nearest_of_two_same_file_same_rule
- tests/test_gates.py::TestTestGate::test_match_waiver_still_suppresses_regardless_of_which_one_wins
designated_repro_test: tests/test_gates.py::TestTestGate::test_match_waiver_picks_line_nearest_of_two_same_file_same_rule
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 43791e5c5149634379237c60958855d71623d625
---
T-2321 added 3 distinct `frob:waive PERF008 reason="..."` comments in
`src/frob/app/ticket_runner/_land_cmd.py`, two with DIFFERENT reason
text (one about a per-porcelain-block invariant, one about the T-1913
retry race). Both waivers correctly suppressed their findings (measured:
gate:PERF errors 3->2, warnings 52->50, waived 116->119, exactly +3),
but `frob check`'s own printed `[waived: ...]` annotation for BOTH
PERF008 findings in that file showed the SAME reason text (the T-1913
retry-race one) even though the two waiver comments in the source are
textually different and sit at different lines/functions.

Suppression itself is correct (`_match_waiver`, presumably keyed by
(file, rule) or similar, not (file, rule, line) precisely enough for
display purposes) -- this is a REPORTING/attribution defect, not a
suppression defect: the reason shown for one specific finding can be a
DIFFERENT waiver's reason when a file has 2+ waivers for the same rule
id. For a repo whose whole pitch is "waivers are an accountable, honest
audit trail", a misattributed reason is a real correctness gap in that
trail, even though it never causes an unintended suppression.

Reproduce: add two `frob:waive PERF008 reason="A"` and
`frob:waive PERF008 reason="B"` comments (different reasons) above two
different PERF008 sites in the same file, run `frob check --only perf`,
and check whether each finding's printed `[waived: ...]` text matches
ITS OWN comment or the other one.

Investigate `src/frob/gates/_waive.py::_match_waiver` for how it
selects a reason string among 2+ waiver comments for the same
(file, rule) pair, and make the match line-precise if it is not
already.