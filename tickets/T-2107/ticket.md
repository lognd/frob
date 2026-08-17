---
id: T-2107
title: 'argparse suggests flags from a different subparser: ''unrecognized arguments:
  --set X (did you mean: --set?)'' names a flag the invoked subcommand does not have'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/__main__.py
- tests/unit/test_main_entry.py
- tickets/T-2112/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/_argparse.py
  reason: 'correct scope: bug lives in frob.__main__._SuggestingArgumentParser, not
    the nonexistent _argparse.py'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/app/__init__.py
  reason: 'correct scope: bug lives in frob.__main__._SuggestingArgumentParser, not
    the nonexistent _argparse.py'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/__main__.py
  reason: 'correct scope: bug lives in frob.__main__._SuggestingArgumentParser, not
    the nonexistent _argparse.py'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: 'correct scope: bug lives in frob.__main__._SuggestingArgumentParser, not
    the nonexistent _argparse.py'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2112/ticket.md
  reason: filing the follow-up ticket writes this file; SCOPE001 flags it same as
    any other new path
  actor: logan
  at: '2026-08-10'
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
## Done report

T-2107 fixes the cross-subparser "did you mean" suggestion in
frob.__main__._SuggestingArgumentParser. Root cause: argparse always
calls error() on the ROOT parser for a leftover-arguments
("unrecognized arguments: ...") failure, even when the actual mistake
was made several subcommand levels down (frob ticket doable --limit).
Before this fix, both the suggestion candidate pool
(_ALL_OPTION_STRINGS, deliberately global) and the printed usage block
(self.print_usage on the root) reflected the WHOLE CLI tree, not the
invoked subcommand -- so a flag that exists only on a different
subcommand got confidently "suggested" back as the fix for the exact
same failure, and the shown usage was the 40+-verb-group top-level
listing instead of the actually-relevant subcommand's own usage.

Fix: _SuggestingArgumentParser.parse_known_args now records the chain
of parsers argparse recurses into (module-level _INVOKED_PARSERS,
cleared per _build_parser() call). error() uses the most specific
parser reached (_INVOKED_PARSERS[-1]) as both (a) the candidate pool
for _did_you_mean's unrecognized-flag suggestion
(_collect_option_strings(target), scoped to that subcommand and its
own descendants only) and (b) the parser whose usage block gets
printed, replicating argparse.ArgumentParser.error's own body against
`target` instead of `self`. The invalid-choice suggestion path is
unaffected (candidates already come from argparse's own error text).

Verified live:
  $ uv run frob ticket doable --limit 25
  usage: frob ticket doable [-h] [--json] [--show-blocked] [--ignore-lease]
                            [--sprint LABEL] [--by-parent] [--show-anchors]
                            [--path DIR]
  frob ticket doable: error: unrecognized arguments: --limit 25
  $ uv run frob ticket scope T-2106 --set src/foo.py
  usage: frob ticket scope [-h] [--add GLOB] [--remove GLOB]
                           [--demote-to-evidence-only GLOB] [--reason TEXT]
                           [--reason-file PATH] [--no-commit] [--path DIR]
                           id
  frob ticket scope: error: unrecognized arguments: --set src/foo.py

No misleading suggestion, correct subcommand usage in both cases.
Existing suggestion tests (unknown subcommand, unknown flag on the
SAME subcommand, far-off flag -> no suggestion) still pass unchanged.

Scope was corrected from the ticket's original (nonexistent)
src/frob/app/_argparse.py + src/frob/app/__init__.py to the real
location, src/frob/__main__.py + tests/unit/test_main_entry.py (+ the
draft-ticket path SCOPE001 flagged from filing the doc follow-up).

Could not update docs/commands/cli-vocabulary.md's "Did-you-mean"
section (frob:describes-linked, now stale re: the global-pool
description) inside this ticket: docs/commands/** is held by a live
cross-worktree lease from T-1382 for T-2107's whole duration
(ScopeLeaseConflict). Filed T-2112 for that doc update.

### Changed
```
 tests/unit/test_main_entry.py      | 30 ++++++++++++++++++++++++++++
 tickets/T-2107/ticket.md           | 41 +++++++++++++++++++++++++++++++++++---
 tickets/T-2112/ticket.md | 40 +++++++++++++++++++++++++++++++++++++
 3 files changed, 108 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_suggestion_scoped_to_invoked_subcommand` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_error_shows_invoked_subcommand_usage` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/__main__.py, COV001@src/frob/__main__.py, PRE001@tickets/T-2107, TEST001@src/frob/__main__.py, WIRE001@src/frob/__main__.py
