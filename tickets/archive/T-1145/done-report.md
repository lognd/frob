## Done report

Investigated T-1145's SCOPE002 debt report (filed while working T-1125:
~548 SCOPE002 warnings, plus one severity-bumped locally to ERROR,
purely from declaring the `src/frob/tickets/**` glob).

Findings: the volume reproduces against any `tickets/**`-scoped ticket
generally, not something T-1125's diff introduced -- confirmed by
re-running `frob check --ticket <id> --only scope` against the queue's
current tickets/**-scoped tickets. Root cause is structural: frob.tickets
is a wide package whose OWN test suite is deliberately split across many
tests/test_tickets_*.py files rather than 1:1 with its internal module
split, so SCOPE002's per-symbol code<->test glob comparison against the
bare package glob produces a large, permanent finding count independent
of what any one ticket touches.

Resolution (docs/design/tickets-package-scope-precedent.md, new):
recorded a decision with two dispositions -- (1) a ticket scoped to one
or two families/files must NOT use the bare package glob (narrow it via
`frob ticket scope --set`, the correct response to TICK009's own
"chronically over-broad glob" nudge); (2) a ticket whose OWN plan is
genuinely package-wide (a redesign, migration, or multi-family residue
sweep) may use the bare glob, and SCOPE002's resulting WARN volume for
THAT ticket is accepted debt, not something to chase to zero (SCOPE002
is already WARN-severity, "a nudge, not a hard block" per
docs/modules/gates.md; no ticket needed -- this is a doctrine statement,
not a disclosed cut).

Applied it to the actual queue: the two open tickets currently declaring
the bare `src/frob/tickets/**` glob (T-1136's ledger-v2 design/migration,
T-1152's multi-family residue sweep following T-1151) both fit
disposition 2 by their own acceptance criteria/body -- neither needed
re-scoping. No open ticket at investigation time was mis-declared under
disposition 1.

Linked the new doc from docs/index.md (DOC001 requires a doc be
reachable from a crawl root; added the one index-list line, in the same
convention every other docs/design/*.md entry uses) -- scope-added via
`frob ticket scope T-1145 --add docs/index.md --reason-file ...` since
this was the minimal in-convention closure, not a widening of the
ticket's actual work.

Verification:
- `uv run frob check --ticket T-1145 --only doclink --only docanchor
  --only drift` -- 0 errors (DOC001 orphan resolved by the index.md
  link).
- `uv run frob check --ticket T-1145 --only prework --only registry
  --only scope` -- gate:REG/gate:SCOPE/gate:WAIVE all pass, 0 errors.
- Docs-only ticket, no new pytest surface of its own -- evidence recorded
  against the existing CLI-dispatch integration test per the T-0167
  precedent (docs/guides/agent-playbook.md section 5).

Filed: none (this ticket's own scope covered the full investigation +
decision; no further split-off work identified).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `cmd:grep -q tickets-package-scope-precedent docs/index.md exit=0 sha256=e3b0c44298fc` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
