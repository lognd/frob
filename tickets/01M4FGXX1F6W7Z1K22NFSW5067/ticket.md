+++
id = "01M4FGXX1F6W7Z1K22NFSW5067"
title = "CAP001 and CAP002 fire and are writable in accept and defer"
type = "story"
category = "in-progress"
priority = "critical"
points = 5
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:16Z"
updated = "2026-10-09T05:33:36Z"
idempotency_key = "logand-gaps-A3"
labels = ["adoption:logand-app", "grimble"]
scope = ["crates/grimble*/**", "changelog.d/**", "docs/design/rules.md", "crates/gob-mdtest/coverage-allowlist.toml", "docs/reference/rules/CAP001.md", "docs/reference/rules/CAP002.md", "docs/reference/rules/README.md"]

[[links]]
kind = "relates"
target = "01M3Z714EEST9EGEHWWV56RXG4"

[[acceptance]]
text = "Given node a owning Python that calls open(), subprocess.run and socket.listen with no grants, when grimble check runs, then CAP001 is an Error for fs.read, exec and net.listen"
bound = false

[[acceptance]]
text = "Given a granted atom never observed in owned code, when grimble check runs, then CAP002 is a Warning"
bound = false

[[acceptance]]
text = "Given accept CAP001 and accept CAP002 on a node, when grimble check runs, then neither is MDL013 and the findings are suppressed and counted"
bound = false

[[acceptance]]
text = "Given the rule list in check --json, when listed, then CAP001 and CAP002 are present"
bound = false
+++

Repros 09-cap-rules-do-not-fire (~/projects/frob-v2-repros/logand-grimble-20261009/09-cap-rules-do-not-fire) and 11-cap-rule-ids-unwritable (~/projects/frob-v2-repros/logand-grimble-20261009/11-cap-rule-ids-unwritable). binding.md 7.2 item 3: observed use of an ungranted atom is undeclared and CAP001 (Error); declared-never-observed is CAP002 (Warn). No CAP rule is registered, so accept CAP001 is MDL013. Slice of ~V56RXG4 (G14). v1 migration note: strata SYS101 (declared never observed) maps to CAP002; REL200/REL201 stay MDL013 until the sysdesign pack (~7JKZD66) registers them, documented in the ticket close note.
