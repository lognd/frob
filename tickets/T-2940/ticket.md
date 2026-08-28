---
id: T-2940
title: 'README.md: add the frob status command-table row/count (T-2911 land-tooling
  workaround)'
state: done
kind: docs
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:/tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/t2940_evidence.sh
  exit=0 sha256=7b41e3087bba
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2911 added `frob status` as a real subcommand but could not update
README.md's command table/count in the same land (see the land-tooling
bug this filed separately) -- the land-time DOC005 pre-merge guard
compares a same-diff README edit against a registry that is necessarily
one commit stale when the diff ALSO adds the new subcommand.

Once T-2911 has landed (main's own live registry then genuinely includes
`frob status`), this follow-up is trivial and should land cleanly on its
own:

- Bump README.md's "N total commands" claim by 1.
- Add the `frob status` row to the command table (Enforcement section,
  near `frob stats`): "Delta-first movement summary: findings
  healed/introduced since the last stamped baseline, verification lag,
  ticket landing velocity (T-2911)".