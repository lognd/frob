+++
id = "01M3AXSDA41S5B5Q8GNAD66H1Q"
title = "dropped: large (multi-MB) values stored in a single Redis key/field"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
parent = "01M3AXSD9Z2T54HFHNCZ91W3YV"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:02Z"
aliases = ["T-6468"]
labels = ["milestone:0.538.0"]
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

Research file, Key-value anti-pattern #5. Static tier: "dynamic-only
(value size is runtime data; linter can flag `.set()` fed directly from
file-read/serialize-of-large-object as a proxy)" -- the proxy shape
(`.set()` fed from a file-read/serialize call) is the SAME shape
STORE120 already files for the relational blob-in-column case; a
redis-specific twin of that proxy would duplicate coverage rather than
add a new static signal, and the genuinely new information (actual byte
size) is runtime-only.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule
