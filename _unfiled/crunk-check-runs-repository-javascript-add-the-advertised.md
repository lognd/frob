+++
id = "01M7AV37ZMX53C3NNTGFA8TB2V"
title = "crunk check runs repository JavaScript; add the advertised static opt-out"
type = "security"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:15:50Z"
updated = "2026-11-13T21:37:23Z"
labels = ["no-story"]
scope = ["crates/crunk-*/**"]

[[acceptance]]
text = "crunk check --static and engine=static never execute repo JS; test proves it."
bound = false
+++

H1: --static and [tailwind] engine=static are advertised but absent; running untrusted repo code is a security risk. Source: frob-audit-grimble-crunk.md (Opus audit).
