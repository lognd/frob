+++
id = "01M4BH8WMBDTAT4R0ST9VT321D"
title = "board reads every ticket's events one at a time: 25 s on 1400 tickets"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-07T15:56:18Z"
updated = "2026-10-07T16:43:44Z"
idempotency_key = "board-per-ticket-events"
labels = ["milestone:2", "area:pm"]
scope = ["crates/frob/src/board_cmd.rs", "crates/frob-ledger/src/**", "crates/frob/tests/board.rs", "crates/frob-ledger/tests/ledger.rs"]

[[acceptance]]
text = "Given this repository's ledger (about 1400 tickets), when frob board runs, then Ledger::synced and the events-tree walk each run once per invocation, not once per ticket (asserted by a call counter or log count in a test)"
bound = true

[[acceptance]]
text = "Given the same input, when board runs before and after the change, then the JSON output is identical"
bound = true
+++

Measured 2026-10-07 with the debug landing binary: frob board takes 25.4 s wall, 23.7 s user, 52 MB RSS. -vv shows 1129 'index opened' and 1126 'diff_names computed' lines: board_cmd.rs calls Ledger::events(id) for every non-done or recently done ticket (and again for in-progress under --brief), and each call re-runs synced() (ref lookup, Index::open of .frob/tickets.sqlite, key check), Self::load, then lists tickets/<id>/events with a tree diff from the empty tree and reads and parses every blob. Fix: a bulk Ledger::events_many / for_each_events that syncs once and walks the tickets tree once; better still, record the time each ticket entered its current category in the index at fold time so board::entered needs no events at all. The in-progress --brief path should reuse the same events rather than reading them twice.
