+++
id = "01M5A5F8CN6EKHGV1C4QZCQZMP"
title = "grimble shrink verb: wire shrink::plan (dry-run default, --apply), owns proposals, excuse prompt"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T13:26:31Z"
updated = "2026-10-19T14:03:51Z"
labels = ["milestone:2"]
scope = ["crates/grimble/**", "docs/design/cli.md"]

[[acceptance]]
text = "Given a model with a grant no detector observes, when grimble shrink runs, then it prints the removal diff and writes nothing; with --apply the grant is removed"
bound = true
+++

Follow-up of ~71BAAE0: grimble_bind::shrink::plan and Plan::apply exist; add the grimble shrink verb in crates/grimble (bind via grimble_check::bind_repo, print Plan::diff, write only with --apply), a verb test, then owns-selector proposals and the interactive excuse prompt. Was blocked by lease overlap with ~RPQKHAV (crates/grimble/src/**).
