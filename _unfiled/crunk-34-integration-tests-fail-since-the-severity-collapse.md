+++
id = "01M61WBFHXRYRQBBW2RWJH9CR5"
title = "crunk: 34 integration tests fail since the Severity collapse made CRAFT rules Error"
type = "bug"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-28T18:28:56Z"
updated = "2026-10-28T21:47:58Z"
scope = ["crates/crunk/tests/**", "crates/crunk-rules/src/rules/craft*.rs", "tests/crunk-parity/divergences.toml"]

[[acceptance]]
text = "all crunk integration tests pass with fixtures that satisfy CRAFT001/005/010 (rules stay at error)"
bound = true
+++

d7ea79ce8e collapsed Severity so CRAFT001/005/010 now fire at error on clean fixtures; crunk check_exit, e2e, init, new, rename, parity, review, hullbreach_exit tests (34) exit 1. Found while working ~9X5NXA3. Decide: give fixtures focus-visible/active/motion, or have the new-rule ramp downgrade CRAFT again.
