+++
id = "01M4095RVEYWMEWQJFT5Y8JFGW"
title = "Wire frob-pm into ticket doctor and the merge driver (milestone.md, cycle.md)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-03T07:03:08Z"
updated = "2026-10-03T11:36:01Z"
labels = ["release:0.532.0"]
scope = ["crates/frob/src/ticket/**", "crates/frob/src/init.rs"]
+++

found while working ~YR8CA0D: frob_pm::PmStore::doctor and frob_pm::merge::resolve exist but nothing calls them. ticket doctor must also run PmStore::doctor (codes E-PM-*), frob init must add gitattributes lines tickets/_milestones/*/milestone.md and tickets/_cycles/*/cycle.md with merge=frob-ledger, and frob merge-driver must dispatch on the path to frob_pm::merge::resolve (ticket.md keeps the ledger resolver). Without it a concurrent edit of one milestone leaves a textual conflict on its frontmatter file that git cannot resolve (no event is lost; events are separate files).
