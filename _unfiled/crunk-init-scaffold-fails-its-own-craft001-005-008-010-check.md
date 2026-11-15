+++
id = "01M626H3EHCCVMGMZRESJTGTM5"
title = "crunk init scaffold fails its own CRAFT001/005/008/010 check"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T21:26:46Z"
updated = "2026-11-15T15:40:12Z"
scope = ["crates/crunk/src/init/**", "crates/crunk/tests/it/init.rs"]

[[acceptance]]
text = "A raw crunk init scaffold passes CRAFT001, CRAFT005, CRAFT008 and CRAFT010 without patching"
bound = true
+++

found while working WJH9CR5: tests patch the fresh scaffold with satisfy_craft; fix RESET_CSS and roles in scaffold.rs so init output passes check
