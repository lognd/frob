---
id: T-1143
title: 'tickets-archive.md: finish parse.rs->parse/mod.rs evidence-path migration
  (T-1099 residue)'
state: done
kind: docs
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:sh -c 'test "$(grep -c "strata-core/src/parse.rs::tests::" tickets-archive.md)"
  = 0 && test "$(grep -c "strata-core/src/parse/mod.rs::tests::" tickets-archive.md)"
  = 101' exit=0 sha256=e3b0c44298fc
designated_repro_test: null
threat: null
component: null
---
T-1099's parse.rs -> parse/mod.rs rename fixed 61 of 107 stale
`strata-core/src/parse.rs::tests::X` frob:tests evidence citations in
tickets-archive.md via mechanical path-only substitution (same qualname,
`parse::tests::X`, just physically relocated to parse/mod.rs). 40 more
remain (COV003-flagged, e.g. T-0138/T-0226/T-0629/T-0700/T-0702's Done
report "Changed:" bullet lists use `- strata-core/src/parse.rs::tests::X`
form, not the `Evidence:` form my earlier sed pass targeted/verified) --
apparently reappeared or were missed across a `git merge main`/land cycle
mid-T-1099; confirmed present in tickets-archive.md on main today via
`git show main:tickets-archive.md | grep -c`.

Fix: same mechanical substitution,
`strata-core/src/parse\.rs::tests::` -> `strata-core/src/parse/mod.rs::tests::`,
across the remaining occurrences in tickets-archive.md. No narrative content
touched, path-only.