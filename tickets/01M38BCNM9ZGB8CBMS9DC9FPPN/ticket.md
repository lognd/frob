+++
id = "01M38BCNM9ZGB8CBMS9DC9FPPN"
title = "TIER003: epic closer -- all stories done plus a named outcome check recorded on the epic"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5769"]
labels = ["milestone:v0.536.0"]
scope = ["src/frob/gates/_tickets_gate.py"]

[[links]]
kind = "blocked-by"
target = "01M38BCNKNNP946KQM58NCCGXR"
+++

TIER003: epic closer -- all stories done PLUS a named outcome check (invariant or measured metric) recorded on the epic itself. Lands at WARN.

Positive control: an epic with all stories done but no outcome-check field fails TIER003 (expected to catch several of the 42 existing epics); an epic with the field bound and satisfied passes and stays quiet.

Doc page: docs/modules/tickets-lifecycle.md

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

## Drop reason
- 2026-09-24: 2026-09-24: duplicate of T-5780 created by a land_compose splice recovering draft T-draft-ea1c92d6 before its promote; T-5780 is the canonical TIER003 leaf (absorbed by T-5780)
