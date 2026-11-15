+++
id = "01M7ETK7YXDYFF9HM71TE2A1YR"
title = "crunk solver: honor or reject scene <style> rules and @media blocks"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T05:24:03Z"
updated = "2026-11-15T05:52:49Z"
labels = ["no-story"]

[[acceptance]]
text = "A scene whose <style> body has rules is refused by solve_scene_html with SolveError::StylesheetNotApplied, not solved unstyled"
bound = true

[[acceptance]]
text = "A scene with an @media block is refused the same way"
bound = false

[[acceptance]]
text = "An empty <style> and inline styles still solve"
bound = false

[[acceptance]]
text = "The reject-vs-honor decision is recorded in docs/design/crunk/stylesheet-solve.md"
bound = false
+++

Crunk audit2 H2. See /home/logan/projects/frob-audit2-crunk.md for evidence and remedy; verify against HEAD first (audit binary was 10 commits stale).
