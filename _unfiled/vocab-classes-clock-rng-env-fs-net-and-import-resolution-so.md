+++
id = "01M4XK7RZJZV3JXN16RWNH8N7X"
title = "Vocab classes (clock, rng, env, fs, net) and import resolution so NEAT013 fire example passes"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-14T16:16:58Z"
updated = "2026-10-28T12:56:04Z"
labels = ["no-story"]
scope = ["crates/grimble-model/src/**", "crates/gob-symbols/src/**"]

[[acceptance]]
text = "NEAT013 example 0 (python time.time()) fires via run_example"
bound = false
+++

Found while working ~YJPYE5V: knob.sources uses callee_vocab(lang,class); no clock/rng/net classes are registered and python 'time' import does not resolve to a unit so 'resolves to' has no target. Unskip example 0 in corpus_tests.rs.

no-story: internal engineering task in grimble-model; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
