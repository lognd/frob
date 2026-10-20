+++
id = "01M38BCNARPR0A1YPRDTGN9BTT"
title = "TICK008 noise: Ticket model missing branch/worktree lease fields"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "agent"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5464"]
labels = ["milestone:v0.534.0"]
scope = ["src/frob/tickets/_models.py", "tests/gates_suite/test_tick.py", "src/frob/tickets/_evidence.py"]
+++

Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean

TICK008 fires 239 WARN violations against the real tickets/ ledger, all
"unknown ledger field 'branch'" / "unknown ledger field 'worktree'".
frob ticket work writes branch: and worktree: frontmatter onto every
in-progress ticket (the cross-worktree lease side-channel) but the
Ticket pydantic model (src/frob/tickets/_models.py) never declared them
as real fields, so pydantic's extra="allow" captures them as unknown
extras and TICK008 (correctly) flags every one.

Fix: add branch: str | None and worktree: str | None as declared Ticket
model fields (this is exactly the "schema-owning feature lands" case
TICK008's own docstring names as the intended resolution path) -- not a
ledger hand-edit, and not loosening TICK008 itself.
