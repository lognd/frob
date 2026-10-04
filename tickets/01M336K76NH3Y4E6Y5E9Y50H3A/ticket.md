+++
id = "01M336K76NH3Y4E6Y5E9Y50H3A"
title = "squawk migration-safety adapter"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M2Y1SS0WSW1HNM4S14V8BH51"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5333"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/sql/_squawk_adapter.py", "src/frob/doctor.py", "tests/fixtures/sql/squawk/**", "docs/guides/install.md", "docs/modules/sql.md"]

[[links]]
kind = "blocked-by"
target = "01M336K76PVKPGD3ZGMGFC5MF4"
+++

_RELEVANT_TOOLS entry for squawk (T-5139 pattern, OPTIONAL_FOR_GATE -- migrations are a narrower relevance than the whole SQL family), relevant_when = a migrations directory exists. Spawn+parse squawk's JSON output into frob Violations: NOT-NULL-without-default, index-without-CONCURRENTLY, lock-taking rewrites. Fixture: a migration file with each planted anti-pattern.
