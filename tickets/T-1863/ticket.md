---
id: T-1863
title: Reusable coordinator scripts under scripts/ (check summary, fleet status, land
  verification)
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/check_summary.py
- scripts/fleet_status.py
- scripts/verify_lands.py
- docs/guides/coordinator-scripts.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The coordinator re-derives the same three analyses by hand, dozens of
times per session, from inline python. That is not a style complaint --
it has produced wrong answers twice today:

1. `frob check --json` nests severity on the DIAGNOSTIC, inside
   `results[].diagnostics[]`, not on the tool record. Reading it one
   level too shallow yields an empty severity histogram, which reads as
   "0 errors". That exact misread produced two false green reports on a
   red tree.
2. Verifying a land means `git merge-base --is-ancestor <sha> main`. A
   mistyped sha prefix resolves to nothing and, if the script conflates
   "unresolvable" with "not an ancestor", reports LOST WORK for a ticket
   that landed fine. That happened twice.

Both are single-expression facts that must live in exactly one place.

DELIVER three scripts under `scripts/`:

- `check_summary.py` -- run/parse `frob check --json`, print the
  severity histogram and a per-rule error breakdown. The traversal is
  `for record in report["results"]: for diagnostic in
  record["diagnostics"]`.
- `fleet_status.py` -- root dirt (`git status --short`), held leases
  (`.git/frob-leases/*.json` -> ticket id, worktree), and per-worktree
  idle age. This is the pre-dispatch safety check.
- `verify_lands.py` -- given ticket/sha pairs, report ancestor-of-main
  plus commit subject. MUST distinguish `UNKNOWN-SHA` (does not resolve)
  from `MISSING` (resolves, not an ancestor). Conflating them is the
  bug this exists to prevent.

WHY THIS NEEDS TO BE A TICKET. A first attempt was hand-landed and put
27 errors on main: COV001 and TEST001 on every public symbol,
SELFAUDIT001 x4 for the `exec` capability from `subprocess.run`, and
REL001. It was reverted (ae567c5a2). Anything under `scripts/` is
tracked code and every gate walks it. So this ticket must also:

- add `frob:doc` edges for every public symbol (new
  `docs/guides/coordinator-scripts.md`),
- resolve TEST001 -- either real unit tests, or a path-class exemption
  for `scripts/**` in `_test001_002`, mirroring the
  `.claude/hooks/` precedent T-1861 landed. Prefer the exemption only
  if the hooks precedent genuinely covers this shape; otherwise write
  the tests,
- declare a `scripts_ops` node in `design/frob.strata` with the `exec`
  capability the `subprocess.run` calls need (SELFAUDIT001),
- bump the version for REL001.

Verify with a FULL UNSCOPED `uv run frob check` before landing. Skipping
that is what put the 27 errors on main the first time.
