+++
id = "01M64VBRHX20P2EJGQ2S1VG0FG"
title = "CAP: capability detection for C and C++ (audit cc01), include-resolved"
type = "story"
category = "in-progress"
priority = "high"
points = 8
reporter = "lognd"
created = "2026-10-29T22:09:20Z"
updated = "2026-10-31T03:10:09Z"
scope = ["crates/gob-languages/**", "crates/gob-symbols/**", "crates/grimble-check/tests/symbolic_audit.rs", "crates/gob-caps/**", "docs/design/universal-model.md", "crates/gob-plan/src/catalog/answer.rs", "crates/grimble-bind/src/caps.rs"]

[[acceptance]]
text = "C and C++ files are parsed with tree-sitter and capabilities (process, fs, net, env, ffi) are decided from include-resolved call nodes, not raw text"
bound = false

[[acceptance]]
text = "Calls through function pointers or macros report Unresolved, never a silent pass; audit case cc01 is pinned in symbolic_audit and the symbolic guard covers the new adapter"
bound = false
+++

Split from PKW7X2J. C has no Language variant or grammar. Needs: grammar plus detect, include/macro-aware resolution (system, popen, exec*, fopen, open, socket, connect, bind, getenv, dlopen); calls through function pointers or macros are Unresolved. Pin audit case cc01.
