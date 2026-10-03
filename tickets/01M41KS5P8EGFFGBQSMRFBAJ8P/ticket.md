+++
id = "01M41KS5P8EGFFGBQSMRFBAJ8P"
title = "ticket doctor flags every early-closed cycle (E-PM-CONFLICT) and same-day cycles (E-PM-ALIAS) since state and alias suffix became derived"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-03T19:27:44Z"
updated = "2026-10-03T19:42:48Z"
scope = ["crates/frob-pm/src/cycle/**", "crates/frob/src/cycle_cmd.rs", "crates/frob/tests/cycle.rs", "crates/frob-pm/src/doctor.rs", "crates/frob-pm/src/store.rs", "crates/frob-pm/src/event.rs", "crates/frob-pm/src/fold.rs", "crates/frob-pm/src/model.rs"]

[[acceptance]]
text = "Given a cycle created today and closed early, when ticket doctor runs, then it reports no E-PM-CONFLICT"
bound = true

[[acceptance]]
text = "Given two cycles created the same day with the same window, when ticket doctor runs, then their stored aliases differ and no E-PM-ALIAS is reported"
bound = false

[[acceptance]]
text = "Given a ledger that already holds duplicate cycle aliases, when ticket doctor --fix runs, then the duplicates get suffixes in creation order and a second doctor run is clean"
bound = false
+++

Reported by goway, reproduced 2026-10-03 with cycle_days = 2: cycle new --start today, cycle close (early), cycle new --start today. Then ticket doctor reports (a) E-PM-CONFLICT 'event ... changed state expecting active but found planned': ~0MQNY3G derives active from the clock but the stored state stays planned, while the close event records from=active; doctor's fold compares against the stored value. (b) E-PM-ALIAS 'alias 2026-10-03..2026-10-04 names 2 cycles': cycle list shows the second as ...04.2 but the stored alias is identical. Fix both at the source so every reader agrees: the fold/doctor must judge a transition against the derived state at the event's time (one function, lifecycle::state_on), and the disambiguating suffix must be assigned once at creation and stored (alias unique by construction), with doctor --fix able to repair ledgers that already hold duplicate aliases (assign suffixes in creation order) without rewriting history beyond what doctor already does. Find the doctor code (grep E-PM-CONFLICT) and widen with exact paths.
