+++
id = "01M43ATBPPR5QCY0CSPPTNEDQ0"
title = "Rules LAYER001 and ORG001-005 (Rust now, GRL follow-up)"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:29:35Z"
updated = "2026-10-09T16:38:49Z"
idempotency_key = "crunk-plan-rorg"
labels = ["area:crunk", "creates:crates/crunk-rules/src/rules/layer001*", "creates:crates/crunk-rules/src/rules/org00*"]
scope = ["crates/crunk-rules/src/layers/**", "crates/crunk-rules/src/org/**", "crates/crunk-rules/tests/org*.rs", "crates/crunk-rules/tests/layers*.rs", "crates/crunk-rules/src/rules/mod.rs", "crates/crunk-rules/src/lib.rs", "crates/crunk-rules/src/sheets.rs", "crates/crunk-rules/tests/rules.rs", "docs/crunk/rules/README.md", "changelog.d/01M43ATBPPR5QCY0CSPPTNEDQ0*", "crates/crunk-rules/src/rules/layer001*", "crates/crunk-rules/src/rules/org00*"]

[[links]]
kind = "blocked-by"
target = "01M43ARY91XZ35DN9SCHRHS033"

[[links]]
kind = "blocked-by"
target = "01M43ATASM383KB9130JY79XVV"

[[acceptance]]
text = "Given z-index 99 not in [layers], when checked, then LAYER001 fires"
bound = false

[[acceptance]]
text = "Given a stylesheet in no declared bucket, when checked, then ORG005 fires"
bound = false

[[acceptance]]
text = "Given a class `Card_Title` and class_case kebab, when checked, then ORG002 fires"
bound = false
+++

Port rules/_layers.py and _org.py: z-index not a declared layer; bucket placement, class case, component prefix, custom props outside the tokens file, ungoverned sheet. These are membership and shape tests over declarations, so they are the candidates for GRL; they ship first as Rust so parity does not wait for the GRL executor (D76 allows recorded tier-0 exceptions, plugins.md section 4), and the GRL ticket replaces them. Port tests/unit/test_rules_org.py, e2e 04, 12, 13, 14.
