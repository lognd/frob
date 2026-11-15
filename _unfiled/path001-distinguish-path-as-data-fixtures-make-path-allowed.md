+++
id = "01M5XPZJAAX4ZKHGSQGAHK30R3"
title = "PATH001: distinguish path-as-data fixtures, make [path] allowed configurable"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-27T03:38:06Z"
updated = "2026-11-15T22:48:03Z"
scope = ["crates/grimble-lints/**"]

[[acceptance]]
text = "PATH001 ignores multi-line, regex and key: value strings; Options::with_allowed adds configured [path] allowed literals"
bound = true
+++

Found while working ~ZX7DH32. PATH001 cannot tell parser/scrubber input paths (Windows paths) from host paths; false positives on YAML strings like "a:\n  b: [1\n", backslash-newline continuations and regexes starting /home/|/tmp/; [path] allowed is only Options::default() and not wired to config; no accept/attest verb besides frob ack (EXC005 warns until ack).
