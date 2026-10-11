+++
id = "01M4M52WKHGXADHPQ08J1AS8BJ"
title = "gob-cache stops depending on gob-exec: canonical and git_common_dir move to gob-fs (audit M8 slice)"
type = "task"
category = "todo"
priority = "medium"
parent = "01M4CTE0GYDX0XW64JRNF2ZMQG"
reporter = "lognd"
created = "2026-10-11T00:16:28Z"
updated = "2026-10-11T01:16:10Z"
scope = ["crates/gob-fs/**", "crates/gob-cache/**", "crates/gob-exec/**", "changelog.d/**"]
+++

Split from ~NF2ZMQG. gob-cache uses gob_exec::canonical and re-implements git common-dir discovery (lib.rs 222-244). Move both to gob-fs and re-export from gob-exec. Acceptance: no gob-cache -> gob-exec edge in cargo metadata.
