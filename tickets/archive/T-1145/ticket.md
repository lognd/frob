---
id: T-1145
title: 'scope: SCOPE002 closure debt across src/frob/tickets/** ticket-scope globs'
state: done
kind: docs
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/**
- tickets.md
- docs/index.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/index.md
  reason: 'DOC001 requires the new docs/design/tickets-package-scope-precedent.md

    to be linked from somewhere (docs/index.md is the crawl root every other

    docs/design/*.md entry is listed from); adding one index-list line is

    the minimal, in-convention fix, not a scope expansion of the ticket''s

    actual work.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- cmd:grep -q tickets-package-scope-precedent docs/index.md exit=0 sha256=e3b0c44298fc
designated_repro_test: null
threat: null
component: null
---
frob check --ticket T-1125's gates-fast pass surfaces ~548 SCOPE002
"scope closure" warnings (plus one promoted to ERROR) purely from T-1125's
declared scope glob `src/frob/tickets/**` -- every symbol under that whole
package whose bound frob:tests target lives in a test file outside the
ticket's own scope trips it, unrelated to what any single ticket in this
family actually touches. Confirmed pre-existing (not introduced by
T-1125's diff): the same finding count reproduces against tickets/**-scoped
work generally, not just T-1125's specific renumber/prose change.

This is systemic scope-declaration debt for the tickets package (broad
`src/frob/tickets/**` scope globs are common across this ticket family --
see TICK009's own "chronically over-broad glob" findings for T-1109/
T-1110/T-1111/T-1135/etc naming the same package). Investigate either:
(a) a project-level scope-closure precedent/waiver for this package (its
    test suite is intentionally split across many tests/test_tickets_*.py
    files, not 1:1 with source files), or
(b) actually narrowing every ticket's scope in this family to specific
    files+the one or two test files it truly touches, instead of the
    broad glob.

Filed while working T-1125; out of that ticket's own scope to fix.