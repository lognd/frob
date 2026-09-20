---
id: T-5134
title: 'Remove ticket citations (T-####) from all user-facing help and docs: argparse
  help strings, docs/, refusal and remedy text'
state: queued
kind: docs
origin: human
created: '2026-09-20'
priority: high
parent: T-2994
tier: story
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/*.py
- docs/**/*.md
scope_breadth_ack: true
scope_breadth_ack_reason: 'owner directive 2026-09-20: a repo-wide text migration;
  each file is a mechanical citation strip'
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the full CLI, when every 'frob ... --help' output is captured, then
    no output contains a T-#### token
  evidence: []
- text: given docs/ excluding docs/audits and the tickets tree, when scanned, then
    no prose line contains a T-#### token
  evidence: []
- text: given a new help= string containing T-1234, when frob check runs, then the
    DOC lint fires with the file and line
  evidence: []
threat: null
component: cli
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-20: ticket prose (T-#### citations) is removed in its entirety from frob documentation and help. Measured: 462 T-#### mentions across src/frob/_cli_parsers/*.py alone (visible in every --help output, e.g. 'free-form sprint commitment label (e.g. 2026-W30, sprint-14, T-0715)'), plus the docs/ prose T-4422 (DOC012) already covers. Scope of THIS story: (1) argparse help/description/epilog strings in src/frob/_cli_parsers and any runner-side help text: strip the citation, keep the sentence, move any WHY worth keeping into the ticket ledger or a docs/design page; (2) refusal and remedy messages the user reads at the terminal (the 'T-2006 dropped N stale...' log lines are fine as INFO logs, but ERROR text and remedies must not cite tickets); (3) docs/ prose beyond T-4422's DOC012 scope: tables, headings, code-fence captions; (4) a lint so it cannot recur: extend DOC012 (or add DOC013) to fire on a T-#### token inside an argparse help= / description= string literal and inside docs/ prose outside the tickets ledger and docs/audits history; the ledger, done-reports, frob:ticket directive comments, commit messages and CHANGELOG remain the only homes for ticket ids. Coordinate with T-4422 (docs prose) and T-4691 (source comment narrative) so the three stories do not collide on the same files: this story owns _cli_parsers and user-facing message strings; T-4422 owns docs/ prose; T-4691 owns source comments.