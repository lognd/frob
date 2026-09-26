---
id: T-6573
title: DSTACK001 Tier-A merge emits the multi-target frob:doc/frob:tests header as
  one physical line without the continuation wrap, so land trips E501 on a file that
  was clean
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/gates/_fix_engine_text.py
- src/frob/gates/_fmt_directives.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names external paths (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-26'
  old_length: 1431
  new_length: 1537
- mode: append
  reason: 'crunk data point: formatter emits a continuation form DSL001 rejects'
  actor: logan
  at: '2026-09-26'
  old_length: 1527
  new_length: 2252
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the crunk session (2026-09-26), reproducible twice on crunk
T-0169: `frob ticket land` refused with "ruff check found 1 NEW
violation(s) in this ticket's own touched file(s): src/crunk/gallery/
manifest.py:361: E501 Line too long (134 > 88)" while the worktree,
the merged tree and `--dry-run` are all clean. Line 361 is a 64-char
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->`# frob:doc docs/design/subsystems/gallery-manifest.md#public-api`
followed by a second stacked `# frob:doc ...#migrating-v1-to-v2-t-0169`;
64 + 1 + the second target is exactly 134. Cause, verified on dev
b41443f46d: the land's pre-land Tier-A step runs `fix_dstack001_merge`
(T-4713), which collapses a stacked same-kind run into one multi-target
header line and never re-wraps it through the directive formatter's
canonical continuation form, so the scoped ruff pass that follows sees a
new E501 the agent never wrote. The dry run skips Tier-A (T-4179), so it
cannot show it.

Deliver: the DSTACK001 merge emits its header through the same
canonical-lines writer `frob format --directives` uses (backslash
continuation under the E501 limit), and any Tier-A rewrite that lengthens
a line runs that wrap before the land's ruff pass. Positive control: two
stacked 64-char frob:doc lines above one symbol; after the fix the merged
header is wrapped and ruff reports nothing. Related: T-6589
(scope-restrict Tier-A at land), T-6535, T-draft-741eded5 (DSTACK001
malformed output).


Second data point (crunk-ba, 2026-09-26): the backslash-continuation form
suggested as a workaround fails build_graph with DSL001 "continuation join
lands inside the target token", and so does the form `frob format
--directives` itself emits, so the formatter produces a header its own
parser rejects. The only form that parses (0 malformed, both doc edges
present) AND is format-canonical is a comma after the first target:
    # frob:doc a.md#x, \
    # b.md#y
Deliver, in the same change: the DSTACK001 merge and `frob format
--directives` both emit that comma-separated canonical form, and a
round-trip test (format -> parse_directives -> identical edge set) is the
positive control for every multi-target header kind.
