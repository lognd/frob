+++
id = "01M4A61GB9Y9M45R78K2Z70Y1B"
title = "Wire the ticket-branch layout into the merge-driver verb and .gitattributes generation"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-07T03:20:47Z"
updated = "2026-10-09T20:29:39Z"
labels = ["area:mirror", "creates:crates/frob/tests/merge_driver_branch.rs"]
scope = ["crates/frob/src/ticket/merge_cmd.rs", "crates/frob/src/init.rs", "crates/frob/src/ticket/branch_cmd.rs", "crates/frob-ledger/src/branch.rs", "crates/frob-ledger/src/layout.rs", "crates/frob/tests/ticket_branch.rs", "changelog.d/**", "crates/frob/tests/merge_driver_branch.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX82TWWY2616S1Q5N48KNK"

[[acceptance]]
text = "Given a ticket-branch checkout where two branches add events to one ticket, when merged through git, then the driver unions the events and refolds the file"
bound = false

[[acceptance]]
text = "Given the Branch layout, when init writes attributes, then .gitattributes holds the layout's patterns"
bound = false
+++

Found while working ~5N48KNK (blocked there by the lease on crates/frob/**). frob-ledger now has merge::locate, merge::resolve_at and layout::attribute_patterns(layout, dir, attr); merge_cmd.rs still calls ticket_id_of_path and reads side events with a Dir ledger, and init.rs attribute_lines is Dir-only. Make the verb use merge::locate (pass %O %A %B texts), open the ledger with_layout(Branch) when located so side events come from .events/<ULID>/, and have init and ticket branch init write layout::attribute_patterns for the layout onto the branch. Add a CLI test: two branches of a ticket-branch checkout both add events, git merge, driver unions and refolds.
