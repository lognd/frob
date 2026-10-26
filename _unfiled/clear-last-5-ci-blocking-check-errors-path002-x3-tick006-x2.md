+++
id = "01M5V7YGQV7T97D8H8WASZTGHT"
title = "Clear last 5 CI-blocking check errors (PATH002 x3, TICK006 x2)"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-26T04:36:54Z"
updated = "2026-10-26T04:48:54Z"
scope = ["crates/crunk-ingest/tests/**", "crates/crunk-tailwind/src/runtime/**", "crates/frob-check/tests/it/**", "crates/frob-check/src/**", "docs/**"]

[[acceptance]]
text = "frob check reports zero error findings on Linux (PATH002 in crunk-ingest ingest.rs, crunk-tailwind notice.rs, frob-check sibling.rs fixed with Path ops)"
bound = true

[[acceptance]]
text = "TICK006 on the two ticket bodies (_unfiled dsl001 and m2 tick006) cleared without rewriting history, or rule corrected if false positive"
bound = false
+++

CI run on 015d826e2b failed at frob check with 22 errors; Q47G9ZW cleared 17, these 5 remain (verified locally). Exit criterion 6.
