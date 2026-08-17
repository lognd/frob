---
id: T-2112
title: docs/commands/cli-vocabulary.md drifted by T-2107's did-you-mean scoping fix
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/commands/cli-vocabulary.md
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
land_commit: f5d6e7f98b64116139471e3aaad10c381ae395f0
---
T-2107 fixed the cross-subparser did-you-mean suggestion in
src/frob/__main__.py (_SuggestingArgumentParser now scopes both the
suggestion candidate pool and the printed usage block to the
actually-invoked subcommand, T-2107's own fix). docs/commands/
cli-vocabulary.md's "Did-you-mean" section still describes the OLD,
pre-fix behavior (a deliberately global, cross-subcommand candidate
pool) and needs updating to match -- it is frob:describes-linked to
_SuggestingArgumentParser/_did_you_mean, so it will drift the moment
this lands.

Could not be done inside T-2107 itself: docs/commands/** is held by a
live cross-worktree lease from T-1382 for the duration of this ticket
(ScopeLeaseConflict on `frob ticket scope T-2107 --add
docs/commands/cli-vocabulary.md`). Update the "Unrecognized flag"
bullet to say candidates/usage are scoped to the invoked subcommand and
its descendants (_collect_option_strings(target), not the whole CLI
tree), and note _INVOKED_PARSERS / the parse_known_args-recorded
invocation chain as the mechanism.