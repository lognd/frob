---
id: T-2115
title: 'COV001/TEST001: _SuggestingArgumentParser.parse_known_args public with no
  doc/test edge (T-2107 regression)'
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
