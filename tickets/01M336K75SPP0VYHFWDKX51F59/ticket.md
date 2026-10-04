+++
id = "01M336K75SPP0VYHFWDKX51F59"
title = "frob ticket reconcile --strip-stale-fields: remove pydantic-extra fields (branch/worktree from an older writer) from live ledger records so TICK008 stops flagging the real ledger"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5305"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/tickets/_store.py", "tests/test_ticket_reconcile.py", "src/frob/tickets/_reconcile.py", "src/frob/app/ticket_runner/_lifecycle.py", "src/frob/_cli_parsers/_ticket/_progress.py", "src/frob/app/config.py", "src/frob/app/_config_external.py"]
+++

Found while working T-5292 (CI: test_real_repo_ledger_is_tick008_clean): ~35 live tickets carry stale 'branch'/'worktree' extra fields written by an older ledger writer; TICK008 flags them, hand-editing tickets/*.md is forbidden, and no frob verb can strip them. Add a reconcile mode (or a one-shot migrate verb) that drops fields the current Ticket model does not declare, logs each id and field, commits once, and is idempotent; then T-5292's test passes on the real ledger. Positive control: a fixture ledger with one record carrying an extra field is cleaned and a second run is a no-op.
