+++
id = "01M3AXSDBYE1CG3KZ4M9GE195T"
title = "a11y gate: give a11y_findings a real repo root so _locate_statement_page can leave test-only status"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "low"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T21:01:26Z"
aliases = ["T-6526"]
labels = ["milestone:0.534.0", "v1-cluster:B2", "area:crunk"]
scope = ["src/frob/webapp/_a11y_statement.py", "src/frob/gates/_a11y_gate.py"]
+++

Follow-up split off T-5454 (done) and surfaced while repointing a stale
WIRE002-flagged WIRE001 waiver on `_locate_statement_page`
(src/frob/webapp/_a11y_statement.py:127).

`_locate_statement_page`'s own docstring documents that it is "not wired
into any production caller (only this module's own tests use it
directly) -- kept as a small, explicit-root building block for a future
ticket that widens the hook contract" because `a11y_findings`'s per-file
gate hook (T-5323 contract) has no reliable repo root to check against
from inside a single-file hook invocation.

Scope: give the a11y gate hook a real repo root (or equivalent) so
`_locate_statement_page` can be called from `a11y_findings`'s production
path instead of staying test-only, then drop its WIRE001 waiver.
