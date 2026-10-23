+++
id = "01M5K5SWHDE7FP0FPDHQWH2ZRH"
title = "Declare danger/warning/success roles in the default crunk preset"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-23T01:25:29Z"
updated = "2026-10-23T03:04:36Z"
scope = ["crates/crunk-spec/src/presets/**", "crates/crunk-spec/tests/**", "crates/crunk-rules/tests/**", "tests/crunk-parity/fixtures/e2e/e2e_12_ungoverned/**", "tests/crunk-parity/fixtures/e2e/e2e_54_pathmode/**", "crates/crunk-rules/src/rules/craft008.md", "crates/crunk-check/tests/color001.rs", "docs/reference/rules/CRAFT008.md", "docs/reference/rules/README.md", "changelog.d/01M1QDTYR2FFF5HYHVZP2W1WMP.fixed.md", "changelog.d/01M1QDTYRJ3P3GT8828GCNECVB.added.md", "changelog.d/01M1T07NW78MGWRF7HZQMPSRAV.security.md", "changelog.d/01M1T07NWAFVRT2V4RAPVJ9SQM.added.md"]

[[acceptance]]
text = "Given a project initialised with the default crunk preset, when crunk check runs, then CRAFT008 reports nothing"
bound = false

[[acceptance]]
text = "Given the default preset, when its roles are listed, then danger, warning and success roles are declared"
bound = false
+++

found while working 01M5HM3W18AJZET52BZBEJFYD4: CRAFT008 now fires on the default preset, which declares only a body role; add state roles so a fresh init is clean.
