+++
id = "01M4A61GY4Z5H9C0W92BGHBJ66"
title = "Triage, scrub and privacy walks read and write ticket paths directly (Dir layout only)"
type = "task"
category = "todo"
priority = "medium"
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-07T03:20:48Z"
updated = "2026-10-07T03:20:48Z"
labels = ["area:mirror"]
scope = ["crates/frob-ledger/src/triage.rs", "crates/frob-ledger/src/scrub.rs", "crates/frob-ledger/src/privacy.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX82TWWY2616S1Q5N48KNK"

[[acceptance]]
text = "Given Layout::Branch, when a triage promote, scrub or privacy walk runs, then it finds ticket files and events through ULIDs and passes the ledger fixture tests for both layouts"
bound = false
+++

Found while working ~5N48KNK. triage.rs, scrub.rs and privacy.rs build tickets/<ULID>/ticket.md and tickets/<ULID>/events paths from cfg.dir; under Layout::Branch they must resolve the file through Ledger::ticket_file_at / branch_scan_at and events through layout::branch_events_dir. Must land before the live ledger migration (~128J4NT).
