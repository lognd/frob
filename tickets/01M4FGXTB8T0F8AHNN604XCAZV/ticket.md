+++
id = "01M4FGXTB8T0F8AHNN604XCAZV"
title = "Registry misses core-effects atoms: process.spawn, the fs parent and process.env are MDL016"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:03Z"
updated = "2026-10-09T19:19:34Z"
idempotency_key = "logand-gaps-A1"
labels = ["adoption:logand-app", "grimble"]
scope = ["crates/grimble*/**", "changelog.d/**", "crates/gob-ir/src/registry.rs", "crates/gob-ir/tests/queries.rs"]

[[links]]
kind = "relates"
target = "01M3ZX7JRYNHG0BHJ3ZHC9450N"

[[acceptance]]
text = "Given a node with may process.spawn, may fs and may process.env, when grimble check runs, then none is MDL016 and exec resolves as the alias of process.spawn"
bound = true

[[acceptance]]
text = "Given a granted parent atom fs, when the matrix is built, then its cell is the join of fs.read and fs.write"
bound = true

[[acceptance]]
text = "Given a bare name env with no pack declaring it, when grimble check runs, then MDL016 names process.env as the near miss"
bound = true
+++

Repro 01-atoms-registry-closed (~/projects/frob-v2-repros/logand-grimble-20261009/01-atoms-registry-closed): packs.md section 3 says core-effects registers fs (parent of fs.read/fs.write), process.spawn (exec is its alias) and process.env; grimble check reports MDL016 for process.spawn, fs and env. Slice of ~HC9450N, needed first by the logand model. App-specific atoms (fetch_url, client_storage, html_render, ffi, eval, sql) come from a repo pack, see the repo-pack ticket.
