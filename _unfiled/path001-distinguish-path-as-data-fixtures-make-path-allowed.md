+++
id = "01M5XPZJAAX4ZKHGSQGAHK30R3"
title = "PATH001: distinguish path-as-data fixtures, make [path] allowed configurable"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-27T03:38:06Z"
updated = "2026-10-27T03:38:06Z"
scope = ["crates/grimble-lints/**"]
+++

Found while working ~ZX7DH32. PATH001 cannot tell parser/scrubber input paths (Windows paths) from host paths; false positives on YAML strings like "a:\n  b: [1\n", backslash-newline continuations and regexes starting /home/|/tmp/; [path] allowed is only Options::default() and not wired to config; no accept/attest verb besides frob ack (EXC005 warns until ack).
