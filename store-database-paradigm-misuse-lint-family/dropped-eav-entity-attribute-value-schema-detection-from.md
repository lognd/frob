+++
id = "01M3AXSD899TE57ZW7DDA187V5"
title = "dropped: EAV (entity-attribute-value) schema detection from data shape"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
parent = "01M3AXSD9Z2T54HFHNCZ91W3YV"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:02Z"
aliases = ["T-6409"]
labels = ["milestone:0.538.0"]
+++

Research file, Relational anti-pattern #2. Static tier: "dynamic-only
for detecting 'is this actually EAV' from schema shape; static (config)
once table/column names match the pattern" -- the table/column-name
heuristic alone is too weak to file as a real rule (any generic
`Attribute`/`EntityAttribute`-named model trips it, whether or not the
design is genuinely EAV), and the load-bearing signal (is this table
ACTUALLY being used generically, i.e. attribute-name cardinality/value-
type variance) is runtime data a linter cannot see from source.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule
