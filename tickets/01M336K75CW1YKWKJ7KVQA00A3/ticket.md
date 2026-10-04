+++
id = "01M336K75CW1YKWKJ7KVQA00A3"
title = "TICK008 flags real ledger branch/worktree fields it itself wrote"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5292"]
labels = ["milestone:0.534.0"]
scope = ["tests/gates_suite/test_tick.py", "src/frob/gates/_tickets_gate.py", "src/frob/tickets/_reconcile.py"]

[[links]]
kind = "blocked-by"
target = "01M336K75SPP0VYHFWDKX51F59"
+++

gh run 35717833933 ubuntu Test job; re-verified on dev tip 3acf8c6b30: tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean fails -- ~35 real tickets carry unknown ledger field(s) ['branch','worktree'], gate treats as TICK008 violation on the live repo ledger itself.
