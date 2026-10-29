+++
id = "01M64VBRCNYQ3WC895EYXR6GME"
title = "CAP: capability detection for Go (audit g01), import-resolved"
type = "story"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-29T22:09:20Z"
updated = "2026-10-29T22:09:20Z"
scope = ["crates/gob-languages/**", "crates/gob-symbols/**"]
+++

Split from PKW7X2J. Go has no Language variant or tree-sitter grammar in gob-languages, so no resolved path-use scanner or VocabEntry rows exist. Needs: grammar plus detect, import-resolved scanner (aliases, dot imports, package-qualified names) in gob-symbols lookups, vocab for os/exec, os, net, net/http, os.Getenv, plugin. Pin audit case g01. Unresolvable forms report Unresolved.
