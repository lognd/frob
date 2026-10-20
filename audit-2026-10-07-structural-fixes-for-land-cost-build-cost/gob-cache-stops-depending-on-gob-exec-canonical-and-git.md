+++
id = "01M4M52WKHGXADHPQ08J1AS8BJ"
title = "gob-cache stops depending on gob-exec: canonical and git_common_dir move to gob-fs (audit M8 slice)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M4CTE0GYDX0XW64JRNF2ZMQG"
reporter = "lognd"
created = "2026-10-11T00:16:28Z"
updated = "2026-10-11T03:17:09Z"
scope = ["crates/gob-fs/**", "crates/gob-cache/**", "crates/gob-exec/**", "clippy.toml"]

[[acceptance]]
text = "Given the gob-cache manifest, when its dependencies are read, then gob-exec is not among them, and git_common_dir resolves a primary checkout and a linked worktree to the same directory (test gob_cache_does_not_depend_on_gob_exec)"
bound = true

[[acceptance]]
text = "Given gob-fs, when git_common_dir is called on a primary checkout, a linked worktree and a plain directory, then it returns the canonical shared .git dir for the first two and None for the last (test a_linked_worktree_and_its_primary_share_one_common_dir_and_a_plain_dir_has_none)"
bound = true
+++

Split from ~NF2ZMQG. gob-cache uses gob_exec::canonical and re-implements git common-dir discovery (lib.rs 222-244). Move both to gob-fs and re-export from gob-exec. Acceptance: no gob-cache -> gob-exec edge in cargo metadata.
