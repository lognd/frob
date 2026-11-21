+++
id = "01M7Y5ZP89J1XC63S4448HACSB"
title = "allowed_tools passes code-executing flags: git -c core.sshCommand, --upload-pack, --exec-path run arbitrary programs"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-21T04:31:42Z"
updated = "2026-11-21T04:50:44Z"
labels = ["no-story"]
scope = ["crates/frob-evidence/**"]

[[acceptance]]
text = "Given a command-provider evidence ref whose program is git and whose args carry a config-injection or program-execution flag, when it runs, then it is refused with a typed error naming the flag"
bound = true

[[acceptance]]
text = "Given ordinary git, cargo and python3 invocations used by existing evidence, when they run, then they are unaffected"
bound = true
+++

Audit 2026-11-20 deferred item. allowed_tools matches program names only (documented in 0e41515bb5). Add a small deny-list of execution flags per program (git: -c, --config-env, --upload-pack, --receive-pack, --exec-path, --ext-cmd style; python3: -c, -m with non-allowlisted? decide; cargo: --config) in the command provider. no-story: audit follow-up.
