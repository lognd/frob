+++
id = "01M61WBFHXRYRQBBW2RWJH9CR5"
title = "crunk: 34 integration tests fail since the Severity collapse made CRAFT rules Error"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-28T18:28:56Z"
updated = "2026-10-28T18:28:56Z"
scope = ["crates/crunk/tests/**", "crates/crunk-rules/src/rules/craft*.rs"]
+++

d7ea79ce8e collapsed Severity so CRAFT001/005/010 now fire at error on clean fixtures; crunk check_exit, e2e, init, new, rename, parity, review, hullbreach_exit tests (34) exit 1. Found while working ~9X5NXA3. Decide: give fixtures focus-visible/active/motion, or have the new-rule ramp downgrade CRAFT again.
