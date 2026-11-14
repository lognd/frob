+++
id = "01M5H5P5H1CSMP9Q3NF4RY4M26"
title = "crunk: I18N rules (pseudo-locale expansion, RTL, T1)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T06:44:59Z"
updated = "2026-11-14T18:41:25Z"
scope = ["crates/crunk-rules/src/rules/i18n001.rs", "crates/crunk-rules/src/rules/i18n001.md", "crates/crunk-rules/src/rules/i18n002.rs", "crates/crunk-rules/src/rules/i18n002.md", "crates/crunk-rules/src/i18n.rs", "crates/crunk-rules/src/lib.rs", "crates/crunk-rules/src/rules/mod.rs", "crates/crunk-rules/tests/it/rules.rs", "crates/crunk-rules/tests/it/i18n_rules.rs", "crates/crunk-rules/tests/it/main.rs", "docs/reference/rules/**", "changelog.d/01M7N6MVYC8I18NRTLPSEUDO01.added.md", "crates/crunk-rules/tests/it/support/mod.rs", "changelog.d/01M5H5P5H1CSMP9Q3NF4RY4M26.added.md", "docs/reference/rules/README.md", "docs/README.md"]

[[links]]
kind = "blocked-by"
target = "01M7DKEF5H542R72Z6VGQF7ZAJ"

[[acceptance]]
text = "I18N001 flags length-budgeted keys whose text fits but whose 40% pseudo-locale expansion does not; I18N002 flags physical left/right CSS beside an RTL locale"
bound = true
+++

found while working ~VAAWD0R: I18N T0/T1 rules were cut.
