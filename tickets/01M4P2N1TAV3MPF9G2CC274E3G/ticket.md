+++
id = "01M4P2N1TAV3MPF9G2CC274E3G"
title = "agent: frob agent heavy (native lock, env and test-executable cleanup replacing heavy.sh)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4P2MQ9EDGX3NCSBRS0H1AYB"
reporter = "lognd"
created = "2026-10-11T18:12:27Z"
updated = "2026-10-11T18:12:27Z"
scope = ["crates/frob-cli/**"]

[[acceptance]]
text = "heavy takes the shared build lock under the git common dir, sets the target dir, runs the command, cleans regenerable test executables, releases the lock"
bound = false

[[acceptance]]
text = "lock is released on failure and on interrupt"
bound = false

[[acceptance]]
text = "concurrent heavy invocations serialize"
bound = false
+++
