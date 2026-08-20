---
id: T-2704
title: DOC008/DOC011 normalize ../ with a string replace instead of path resolution,
  breaking every valid parent-relative link (2 sites)
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_doclink_docanchor.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_doclink_docanchor.py
  reason: ../ resolution fix for DOC008/DOC011, both sites
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_gates.py
  reason: existing tests for docanchor/doclink gates
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by a downstream consumer repo (aprog-public) on frob 0.530.0,
2026-08-20. 10 correct parent-relative links reported broken.

## The bug

`src/frob/gates/_doclink_docanchor.py`:

    resolved = str(PurePosixPath(*(base / path_part).parts)).replace("../", "")

The trailing `.replace("../", "")` deletes the `../` TEXT rather than
resolving the parent traversal, so the segment it was supposed to pop
stays in the path.

From `docs/architecture/config-models.md` (base `docs/architecture`), the
link `../../design/mini-quizzes.md`:

    parts   ('docs','architecture','..','..','design','mini-quizzes.md')
    replace -> docs/architecture/design/mini-quizzes.md   (reported broken)
    correct -> design/mini-quizzes.md                     (exists on disk)

The emitted message shows the bug on its face: two `../` segments were
consumed and no directory was popped.

## TWO SITES, not one

The reporter found line 271. Grep finds the identical expression at BOTH:

    src/frob/gates/_doclink_docanchor.py:141
    src/frob/gates/_doclink_docanchor.py:271

Fix both. Fixing only the reported one leaves the same defect live on the
other rule.

## Fix direction

Resolve properly rather than textually -- walk the parts and pop on `..`
(os.path.normpath semantics over the PurePosixPath). KEEP the existing
guard so a link cannot escape above the repo root; a normpath that walks
out of the tree must still be refused, not silently accepted.

## Confirmed-correct downstream links that must pass after the fix

    docs/architecture/config-models.md:83
    docs/contributors/guide.md:29,61
    docs/contributors/quickstart.md:7,32,185,290
    docs/setup/github-and-ci.md:101
    docs/tools/aprog-quizzes.md:4,41

## Positive controls, both directions

- a valid `../`-relative link resolves and does NOT fire
- a link to a genuinely missing file STILL fires (the reporter confirms
  `docs/grader/overview.md:143-146` are genuine misses -- frob is right
  about those, and must stay right)
- a link attempting to escape above the repo root is still refused
