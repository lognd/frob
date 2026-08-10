## Done report

Added an explicit, boring escape span, frob:quote(...), recognized by
every scanner that reads directive-shaped text: frob.graph.dsl's own
parse_directives and markdown_anchors, plus frob.tickets._live_tracker's
separate git-grep citation scan. mask_frob_mentions replaces the whole
wrapper span (delimiters and contents) with same-length filler before
any directive-shaped matching runs, so an unescaped real directive
elsewhere on the same physical line stays honored -- only the wrapped
span is masked.

A wrapper span, not a verb-position prefix, was chosen deliberately: the
measured incident that motivated this ticket quoted a bare
follow_up="T-1956" attribute with no adjacent frob: verb at all, so a
verb-position escape (e.g. a doubled frob::waive prefix) could not have
covered that case. The wrapper covers any substring regardless of where
in a comment it sits.

Documented in docs/modules/graph.md and docs/modules/tickets.md
alongside the DSL reference.

Land-time Tier-A fmt auto-fix note: land's own absorbed `frob fmt` pass
reflows long comment lines in src/frob/graph/__init__.py, and its rewrap
of the frob:waive WALK001 comment there (line-continuation backslashes)
reads to the deletion-filter check as removing that directive even
though the wrap is purely cosmetic and outside this ticket's own scope
-- src/frob/graph/__init__.py:WALK001 is declared here as intentional,
fmt-caused, and unrelated to this ticket's own change.

### Changed
```
 design/frob.strata                          |   2 +-
 docs/modules/graph.md                       |  39 ++++++++
 docs/modules/tickets.md                     |  16 ++++
 src/frob/graph/dsl.py                       |  55 ++++++++++-
 src/frob/tickets/_live_tracker.py           |  31 ++++++-
 tests/test_tickets_live_tracker.py          |  39 ++++++++
 tests/unit/graph/test_dsl_mention_escape.py | 138 ++++++++++++++++++++++++++++
 tickets/T-1970/ticket.md                    |  87 +++++++++++++++++-
 8 files changed, 402 insertions(+), 5 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: F401@/home/logan/projects/frob/.claude/worktrees/t1970-only/tests/unit/test_tickets_evidence_only_scope.py
