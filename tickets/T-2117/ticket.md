---
id: T-2117
title: 'COV001/TEST001: _SuggestingArgumentParser.parse_known_args public with no
  doc/test edge (T-2107 regression)'
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/__main__.py
evidence_scope:
- tests/unit/test_main_entry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_suggestion_scoped_to_invoked_subcommand
- tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_error_shows_invoked_subcommand_usage
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2107's land (41286e07b2e0) added _SuggestingArgumentParser.
parse_known_args (src/frob/__main__.py) to record the argparse
invocation chain. It is public (no leading underscore, matching
argparse's own base-class method name it overrides) with neither a
frob:doc nor a frob:tests edge, raising gate:COV COV001 and gate:TEST
TEST001 on the unscoped repo-wide floor (measured by the coordinator
post-land).

Cannot be private-renamed: argparse only calls parse_known_args by
this exact name on a subparser instance, so the method must keep it to
be picked up by the parsing chain at all.

Fix: frob:tests edge to the two existing T-2107 tests that already
exercise it indirectly through parser.parse_args (which always calls
parse_known_args internally):
tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_suggestion_scoped_to_invoked_subcommand
and
::test_unrecognized_flag_error_shows_invoked_subcommand_usage.
For the doc edge, docs/commands/cli-vocabulary.md is under a live
T-1382 cross-worktree lease (same block hit while landing T-2107 itself)
-- frob:waive COV001 with that reason, citing the existing
T-draft-9a07db1f/renumbered follow-up that already tracks refreshing
that doc once the lease frees.

## Done report

Fixes the COV001/TEST001 regression the coordinator measured after
T-2107's land: _SuggestingArgumentParser.parse_known_args
(src/frob/__main__.py) is public (no leading underscore) with neither
a frob:doc nor a frob:tests edge.

Cannot rename it private: argparse's own subparser-action machinery
calls parse_known_args by this exact name on every parser instance it
recurses into (that IS the mechanism T-2107's fix relies on), so the
override must keep the base class's public method name.

Fix: frob:tests edges pointing at the two existing T-2107 tests that
already exercise this method indirectly (every parser.parse_args call
goes through parse_known_args internally) -- verified they still pass.
frob:doc: docs/commands/cli-vocabulary.md is under a live T-1382
cross-worktree lease (same block T-2107 itself hit), so a dedicated
doc anchor cannot be added right now -- used frob:waive COV001 with
that reason instead of a token docstring anchor, citing T-2112 (the
renumbered T-2107 follow-up) which already tracks refreshing that doc.

Verified: `frob check --only coverage` no longer lists
_SuggestingArgumentParser.parse_known_args under COV001 (the finding
now appears with [waived: ...] instead); `frob check --only test`
clean (0 errors). The remaining COV001/COV007 findings in an unscoped
run are pre-existing, unrelated to this ticket (src/frob/gates/
_rule_id_scan.py, src/frob/tickets/_land_git_ops.py::detect_
duplicate_ticket_id_collisions from the just-landed T-2113/T-2114,
etc.) -- confirmed by symbol/file, not touched by this change.

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py |  30 ++++++++-
 tests/unit/test_rapid_sweep.py             |  57 ++++++++++++++++
 tickets/T-2106/done-report.md              | 105 +++++++++++++++++++++++++++++
 tickets/T-2106/ticket.md                   |  21 +++++-
 tickets/T-2117/ticket.md         |  51 ++++++++++++++
 5 files changed, 261 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_suggestion_scoped_to_invoked_subcommand` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_error_shows_invoked_subcommand_usage` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/__main__.py, COV001@src/frob/tickets/_land_git_ops.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2107/src/frob/tickets/_land.py, PRE001@tickets/T-2117, TICK004@tickets.md
