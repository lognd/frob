---
id: T-1478
title: argument-level may scoping (T-1440 follow-up)
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/strata/surface.md
- src/frob/strata/_mutation_audit.py
- src/frob/strata/_native_staleness.py
- strata-core/src/parse/grammar_node.rs
- src/frob/strata/_ast.py
- src/frob/strata/_models.py
- src/frob/strata/_effects.py
- tests/unit/strata/test_effects.py
- design/frob.strata
- src/frob/strata/_elaborate.py
- docs/strata/roadmap.md
- docs/modules/cli.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: strata-core/src/parse/grammar_node.rs
  reason: 'T-1440''s declared scope excluded every file argument-level may scoping
    actually needs (previous attempt''s failure log): the grammar production adding
    the ''of'' trailer (strata-core/src/parse/grammar_node.rs), the parsed-AST field
    (_ast.py), the elaborated field (_models.py), and the per-argument SYS100 join
    (_effects.py). test_effects.py carries the new regression tests; design/frob.strata
    needs a via-list addition on testsuite''s own env grant since the new test fixtures
    contain real env-read needle literals (self-conformance, same T-1589 precedent).'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_ast.py
  reason: 'T-1440''s declared scope excluded every file argument-level may scoping
    actually needs (previous attempt''s failure log): the grammar production adding
    the ''of'' trailer (strata-core/src/parse/grammar_node.rs), the parsed-AST field
    (_ast.py), the elaborated field (_models.py), and the per-argument SYS100 join
    (_effects.py). test_effects.py carries the new regression tests; design/frob.strata
    needs a via-list addition on testsuite''s own env grant since the new test fixtures
    contain real env-read needle literals (self-conformance, same T-1589 precedent).'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_models.py
  reason: 'T-1440''s declared scope excluded every file argument-level may scoping
    actually needs (previous attempt''s failure log): the grammar production adding
    the ''of'' trailer (strata-core/src/parse/grammar_node.rs), the parsed-AST field
    (_ast.py), the elaborated field (_models.py), and the per-argument SYS100 join
    (_effects.py). test_effects.py carries the new regression tests; design/frob.strata
    needs a via-list addition on testsuite''s own env grant since the new test fixtures
    contain real env-read needle literals (self-conformance, same T-1589 precedent).'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_effects.py
  reason: 'T-1440''s declared scope excluded every file argument-level may scoping
    actually needs (previous attempt''s failure log): the grammar production adding
    the ''of'' trailer (strata-core/src/parse/grammar_node.rs), the parsed-AST field
    (_ast.py), the elaborated field (_models.py), and the per-argument SYS100 join
    (_effects.py). test_effects.py carries the new regression tests; design/frob.strata
    needs a via-list addition on testsuite''s own env grant since the new test fixtures
    contain real env-read needle literals (self-conformance, same T-1589 precedent).'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: 'T-1440''s declared scope excluded every file argument-level may scoping
    actually needs (previous attempt''s failure log): the grammar production adding
    the ''of'' trailer (strata-core/src/parse/grammar_node.rs), the parsed-AST field
    (_ast.py), the elaborated field (_models.py), and the per-argument SYS100 join
    (_effects.py). test_effects.py carries the new regression tests; design/frob.strata
    needs a via-list addition on testsuite''s own env grant since the new test fixtures
    contain real env-read needle literals (self-conformance, same T-1589 precedent).'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: 'T-1440''s declared scope excluded every file argument-level may scoping
    actually needs (previous attempt''s failure log): the grammar production adding
    the ''of'' trailer (strata-core/src/parse/grammar_node.rs), the parsed-AST field
    (_ast.py), the elaborated field (_models.py), and the per-argument SYS100 join
    (_effects.py). test_effects.py carries the new regression tests; design/frob.strata
    needs a via-list addition on testsuite''s own env grant since the new test fixtures
    contain real env-read needle literals (self-conformance, same T-1589 precedent).'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_elaborate.py
  reason: MayGrant elaboration (_elaborate_node) needs the new of= field threaded
    through, missed in the initial scope --add pass
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/strata/roadmap.md
  reason: design/frob.strata is in scope (T-1478's own via-list addition); SCOPE002
    closure requires every doc anchor design/frob.strata's nodes point at (roadmap.md's
    self-hosting-commitments section, cli.md's natives-build anchor) to be in scope
    too, doc-only additions, no code change needed
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/cli.md
  reason: design/frob.strata is in scope (T-1478's own via-list addition); SCOPE002
    closure requires every doc anchor design/frob.strata's nodes point at (roadmap.md's
    self-hosting-commitments section, cli.md's natives-build anchor) to be in scope
    too, doc-only additions, no code change needed
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/strata/test_effects.py::TestArgumentLevelMayScoping::test_argument_matching_of_glob_is_clean
- tests/unit/strata/test_effects.py::TestArgumentLevelMayScoping::test_argument_outside_of_glob_is_a_violation
- tests/unit/strata/test_effects.py::TestArgumentLevelMayScoping::test_of_less_grant_still_covers_every_argument
- tests/unit/strata/test_effects.py::TestArgumentLevelMayScoping::test_via_and_of_compose_as_independent_axes
designated_repro_test: null
threat: null
component: null
---
docs/strata/surface.md documents argument-level `may` scoping (e.g.
`may "env.read" of "FROB_*"`, narrowing WHICH env vars/paths/hosts a
grant covers, not just which files) as deliberately deferred by T-1440's
own scope cut, saying "its own follow-up ticket (T-1440's child) rather
than bundled into the grammar/join landing; see tickets.md for its id" --
but no T-1440 child ticket was ever actually filed. File it for real
(this ticket) and build argument-level may scoping. Found while draining
NEGEXIST001 (T-1477): the doc's absence-claim had no
frob:until binding.

## Failure log
- 2026-08-08 attempt 1: Undoable as scoped: declared scope (surface.md, _mutation_audit.py, _native_staleness.py) excludes the grammar/AST/models/effects files argument-level may scoping actually needs (strata-core grammar, _ast.py, _models.py, _effects.py); needs a re-scoped follow-up, not a silent scope expansion