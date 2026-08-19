---
id: T-2621
title: parse_known_args needs its own doc anchor (T-2612 lease-premise audit)
state: dropped
kind: docs
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- docs/commands/cli-vocabulary.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
src/frob/__main__.py::_SuggestingArgumentParser.parse_known_args carries a
COV001 waiver whose reason cited T-1382's "live cross-worktree lease" on
docs/commands/cli-vocabulary.md as the reason it could not get its own
dedicated frob:doc anchor. T-1382 is now a queued epic holding no lease
(leases bind only at in-progress, T-0453), and T-2112 (done) already
updated that doc's prose to describe T-2107's behavior -- but T-2112 only
touched prose, it never added a `frob:describes` anchor naming
parse_known_args itself. Re-running COV001 with the waiver removed still
fires: the dedicated anchor genuinely does not exist yet.

Add a `frob:describes src/frob/__main__.py::_SuggestingArgumentParser.parse_known_args`
anchor to docs/commands/cli-vocabulary.md (or a short paragraph explaining
the `_INVOKED_PARSERS` recording contract this override adds over
argparse's own method), then remove the COV001 waiver above
parse_known_args once the anchor lands.

Filed by T-2612's lease-premise audit (waiver-removal-vs-owed-work split).

## Drop reason
- 2026-08-19: superseded: the doc anchor was added directly in T-2612 itself (docs/commands/cli-vocabulary.md + frob:doc on parse_known_args) rather than deferred to a follow-up (absorbed by T-2612)
