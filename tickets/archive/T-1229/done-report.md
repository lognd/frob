## Done report

Implemented the NEGEXIST001 mechanism (gate-gap class 3,
docs/audits/docs-staleness-2026-07-29.md): a markdown-side `frob:until
T-####` directive (`<!-- frob:until T-#### -->`, `frob.graph.dsl._UNTIL_RE`)
binds a not-yet-built prose claim ("X does not exist yet", "not yet
built/implemented/wired/supported/available/shipped/landed") to the
ticket that will build it, mirroring `frob:enumerates`'s existing
heading-anchor binding shape. `markdown_anchors` also now heuristically
detects the claim itself (`_NEGEXIST_PHRASE_RE`, deliberately narrow --
a fixed phrase list, not NLP) and emits both an `UNTIL` edge and a new
`CLAIMS_ABSENCE` edge (two new `EdgeKind` members) sharing the doc's
`<doc>#<anchor>` src, so the new gate (`frob.gates._negexist.
negexist001_gate`) never re-reads markdown text -- it groups already-
parsed `GraphSnapshot.edges`.

NEGEXIST001 (WARN, rides alongside DOC004/DOC005/DOC006/DOCENUM001 under
the `docblocks` stage group -- no new stage-group registration needed)
fires two ways: a claim with no `frob:until` at all (unbound), or one
whose bound ticket(s) are all missing/closed/archived (stale). A live
scoped run against this repo's own docs surfaced 4 real, pre-existing
unbound negative-existence claims (docs/modules/gates.md:50/91/456,
docs/modules/graph.md:384) -- the gate works as designed; those 4 are
left for a follow-up burn-down, not fixed here (out of this ticket's own
scope, and fixing them would require either binding a ticket to each or
rewriting the prose, a judgment call for whoever owns that doc).

One gate rule id registered end to end per the T-1428 lesson: NEGEXIST001
added to `_KNOWN_GATE_RULES` (src/frob/gates/_waive.py) and to
docs/design/registry/check-coverage.yaml as exactly one new
`CHK-GATE-NEGEXIST001` entry (`gate_rule_total` bumped 274 -> 275, no
duplicates).

Scope was widened beyond the ticket's original two globs
(src/frob/graph/**, src/frob/gates/**) via `frob ticket scope --add`,
each with a written reason, because implementing the mechanism required
touching adjacent surfaces the original scope did not name:
- docs/design/registry/check-coverage.yaml (the WIRE001/T-1428 registry
  requirement itself)
- docs/modules/gates.md, docs/modules/graph.md (frob:doc anchor targets
  DOC002 must resolve, plus the comment-DSL prose documenting the new
  directive)
- docs/guides/extending/comment-dsl-directives.md (its own
  `frob:enumerates`-checked `_VERB_TABLE` member list went stale the
  moment `until` was added there -- a real DOCENUM001 error, not
  optional)
- tests/unit/gates/test_negexist.py, tests/test_graph.py (evidence)

Self-inflicted findings caught and fixed before landing: my own new doc
prose in gates.md/graph.md illustrating the heuristic's example phrases
("does not exist yet", "not yet built") literally matched
`_NEGEXIST_PHRASE_RE` itself, and `_negexist.py`'s own module docstring
tripped INV006 (an "only" exclusivity claim with no invariant edge).
Both fixed by rewording (bracket-broken example text; dropped the
"only"). WIRE001 also initially flagged the two test-file helper
functions (`_queue`/`_snapshot`) as unreachable outside their own tests
-- renamed to `_test_queue`/`_test_snapshot` so `_is_test_symbol`'s
existing leading-underscore-stripped `test_`/`Test` exemption applies,
matching that function's own documented precedent for private test
helpers.

Verified scoped: `--only docblocks --only wire --only registry --only
invariant --only prework --ticket T-1229` all clean (0 errors); ruff
clean on every touched file; `frob fmt --check` 0 files would change;
`pytest tests/unit/gates/test_negexist.py -q` 10/10 pass. Per playbook
section 6c this is NOT a repo-wide clean claim -- gate families outside
what `--only` named above were not run this session.

### Changed
```
 docs/design/registry/check-coverage.yaml        |   6 +-
 docs/guides/extending/comment-dsl-directives.md |   8 +-
 docs/modules/gates.md                           |  25 ++++
 docs/modules/graph.md                           |  19 ++-
 src/frob/gates/__init__.py                      |   6 +
 src/frob/gates/_negexist.py                     | 127 ++++++++++++++++
 src/frob/gates/_waive.py                        |   3 +
 src/frob/graph/_models.py                       |  17 +++
 src/frob/graph/dsl.py                           |  68 ++++++++-
 tests/unit/gates/test_negexist.py               | 183 ++++++++++++++++++++++++
 tickets.md                                      |  91 +++++++++++-
 11 files changed, 543 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_until_directive_emits_until_edge` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_negative_existence_phrase_emits_claims_absence_edge` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_not_yet_wired_phrase_is_also_detected` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_directive_comment_line_itself_never_matches_the_heuristic` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence::test_plain_prose_with_no_matching_phrase_emits_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_unbound_claim_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_open_ticket_is_clean` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_closed_ticket_is_stale` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_claim_bound_to_missing_ticket_is_stale` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_negexist.py::TestNegexist001Gate::test_no_claims_at_all_is_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 4 error(s), 1279 warning(s), 737 waived
- error-findings: ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/graph/dsl.py, PRE001@tickets/T-1229, SELFAUDIT001@design
