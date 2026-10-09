+++
id = "01M4FJ57NER0WMX4FPNY7E721R"
title = "land runs the full check before evaluating cheap close guards: a missing criteria binding is refused after 47 minutes instead of seconds"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T05:28:44Z"
updated = "2026-10-09T17:45:00Z"
scope = ["changelog.d/**", "crates/frob-land/src/land.rs", "crates/frob-land/tests/land.rs"]

[[acceptance]]
text = "Given a ticket whose acceptance criterion is unbound, when frob land runs, then it refuses with E-DONE-CRITERIA-UNBOUND before merging or checking anything (within seconds), and the order of guards is documented"
bound = false
+++

2026-10-09: ~WAZA1EH land spent 2797 s (cold debug build) and then refused on criteria_evidenced, a ledger-only guard.
