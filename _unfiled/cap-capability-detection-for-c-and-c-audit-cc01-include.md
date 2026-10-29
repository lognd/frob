+++
id = "01M64VBRHX20P2EJGQ2S1VG0FG"
title = "CAP: capability detection for C and C++ (audit cc01), include-resolved"
type = "story"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-29T22:09:20Z"
updated = "2026-10-29T22:09:20Z"
scope = ["crates/gob-languages/**", "crates/gob-symbols/**"]
+++

Split from PKW7X2J. C has no Language variant or grammar. Needs: grammar plus detect, include/macro-aware resolution (system, popen, exec*, fopen, open, socket, connect, bind, getenv, dlopen); calls through function pointers or macros are Unresolved. Pin audit case cc01.
