+++
id = "01M43AVMN1DWBVTYW37JBTM6EF"
title = "Selective import of the crunk repository's 250 tickets (dependent ticket; imports nothing yet)"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:30:17Z"
updated = "2026-10-04T11:30:17Z"
idempotency_key = "crunk-plan-import"
labels = ["area:crunk"]
scope = ["crates/gob-dev/src/import_crunk.rs", "crates/gob-dev/src/import_crunk/**", "crates/gob-dev/tests/import_crunk.rs", "docs/migration/**", "crates/gob-dev/src/main.rs"]

[[links]]
kind = "blocked-by"
target = "01M43A53W5X4PBCXWCTTM4E1PN"

[[acceptance]]
text = "Given the crunk repository, when the importer runs in dry-run, then it prints counts per disposition and every open ticket it would import"
bound = false

[[acceptance]]
text = "Given a frob-friction tracker, when the dry-run lists it, then its disposition and reason are shown and it is not open"
bound = false

[[acceptance]]
text = "Given an imported id, when written, then it is an alias like crunk:T-0042 that cannot collide with a frob T-0042"
bound = false
+++

Same method as ~TM4E1PN, applied to the crunk repository's tickets/ (250: 178 done, 41 queued, 29 dropped, 2 in-progress). Reuse the importer and the mapping-file design; ids become aliases namespaced by source (crunk:T-0042, monorepo.md 5 step 4); done and dropped import as closed history, component crunk. The 43 open ones: product requirements import open under this epic (examples: T-0073, 0074, 0075, 0076, 0077, 0078, 0079, 0080, 0111, 0142, 0158, 0159, 0164, 0166, 0175, 0179, 0202, 0222, 0225, 0226, 0245, 0251, 0258, 0259, 0264, 0283, 0288, 0292, 0294); frob-friction trackers (T-0023, 0024, 0194, 0216, 0237, 0238, 0274, 0280, 0281, 0287, 0291, 0293) and frob policy ticket T-0213 are listed with a reason and import closed as wont-fix history; T-0203 and T-0294 map to this repository's crunk-tailwind and gob-symbols tickets. The mapping is checked-in data reviewed in the PR; the ticket produces a dry-run report (counts, list) and STOPS. Do not run the import: the coordinator reviews and runs it at retirement. Redaction and no-home-path rules apply.
