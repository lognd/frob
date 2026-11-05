+++
id = "01M6PAP4T6PCDKK0BKMDWSEJYE"
title = "Decide per-detector-row versus per-atom aggregation of the atom registry row"
type = "task"
category = "todo"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-11-05T17:04:15Z"
updated = "2026-11-05T17:06:20Z"
labels = ["no-story"]
scope = ["crates/gob-packs/src/tier1/mod.rs"]
+++

Follow-up of ~K4EMP90. rows() takes the first detector row's prose and unions cwe; multiple detector rows per atom lose information.
