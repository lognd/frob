+++
id = "01M6AGNFQ8SCGSVJYRAFMRFH43"
title = "LOG001 precision: file writes by path are advisory (phase 1 of the CI LOG001/LOG002 cleanup)"
type = "bug"
category = "in-progress"
priority = "critical"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T02:57:51Z"
updated = "2026-11-01T07:32:15Z"
scope = ["docs/design/output-atoms.md", "docs/reference/rules/LOG001.md", "crates/grimble-check/src/log/**", "crates/grimble-check/src/rules/log001.md", "crates/grimble-check/tests/log_rules.rs", "crates/crunk-tailwind/node/helper.mjs"]

[[acceptance]]
text = "File writes by path are advisory in the LOG001 atom catalogue (a std::fs::write or open-for-write is not an error), logging.FileHandler still fires, and a test pins both; remaining stdout/stderr call sites are tracked by the follow-up ticket"
bound = true
+++

CI run 41265454676 (d23abc202e) ubuntu frob check: 322 errors, 321 LOG001 (237 'file via ... creates and writes a file by path', 26+19 stdout, 13 file open, 14 stderr, 5 sys.stdout, 3 shell, 3 stream) and 1 LOG002 (crates/crunk-gallery/node/render.mjs:83 no logging crate configured). Top files: frob-land/candidate.rs 17, gob-check/tools.rs 12, frob/init.rs 10, gob-testsupport fake_sibling.rs 8. Earlier runs timed out in grimble (SIB001) so this was hidden. Decide: data file writes are not log output (rule precision) vs real stdout/stderr call sites.
