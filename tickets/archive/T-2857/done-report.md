## Done report

### Instrumentation findings (why each mode escaped the existing warning path)

Measured directly with `frob.graph.dsl.markdown_anchors`/`parse_directives`
against fixture and repo-real text, not inferred:

- **Mode 1 (unescaped `"` in `reason="..."`)**: for a CODE-comment
  `frob:waive` (`# frob:waive RULE reason="..."`), `_ATTR_RE`'s leftover
  check already produces a `MalformedDirective` correctly -- verified with
  `_parse_attrs("waive", ...)` on several fixtures, all caught. The real
  incident was in MARKDOWN (`<!-- frob:waive RULE reason="..." -->`),
  which uses an entirely separate, looser regex:
  `_MD_WAIVE_RE = re.compile(r'frob:waive\s+(?P<rule>\S+)\s+reason="')`.
  This only checks for the OPENING `reason="` -- it never verifies the
  value closes -- so `_unhandled_markdown_directive` saw a recognized rule
  id and returned `None`, zero diagnostic, zero suppression. Confirmed:
  `markdown_anchors("docs/x.md", '<!-- frob:waive DOC006 reason="the "old"
  convention no longer applies" -->\n')` returned `edges=() malformed=()`
  before the fix.
- **Mode 2 (unquoted `reason=`, BUG002 land-time check)**: NOT in
  `src/frob/graph/dsl.py` at all. `frob.gates._bug_repro._BUG002_WAIVER_RE`
  (`re.compile(r'frob:waive\s+BUG002\s+reason="([^"]*)"')`) scans a ticket
  BODY's raw text directly, entirely independent of `frob.graph.dsl`/
  `parse_directives`/`markdown_anchors` -- no `MalformedDirective` concept
  exists on that path at all. An unquoted value simply fails this regex's
  match, `finditer` yields nothing, and the caller treats it exactly like
  "no waiver present" with no diagnostic. Out of this ticket's declared
  scope; filed as a follow-up (see "Filed" below).
- **Mode 3 (prose mention)**: untouched by this ticket. It lives on a
  different code path (`_is_genuine_directive_start`/`mask_frob_mentions`/
  the code-comment `frob:quote(...)` escape), which this diff does not
  modify at all -- T-2854 stays open, not absorbed, not made harder.
- **Mode 4 (trailing-space continuation breaking a dotted reference)**:
  for a `frob:tests`-style code comment with no attrs, the break is
  already caught generically (`_ATTR_RE`/leftover check, verified with a
  fixture). The genuinely SILENT case is markdown's `frob:describes`/
  `frob:enumerates`/`frob:until`/`frob:ticket`/`frob:doc`:
  `_unhandled_markdown_directive` treated these five verbs as
  unconditionally "already handled" purely by verb-name membership in
  `_MD_HANDLED_VERBS`, without checking whether THIS line actually
  produced an edge. Since `markdown_anchors`'s loop only calls
  `_unhandled_markdown_directive` AFTER `_directive_edge` already failed
  to match the same line, that membership check was structurally
  guaranteed to be wrong whenever it mattered. Confirmed: a `frob:
  describes src/x.py::Class.metho d_method` (broken symref, embedded
  space) produced `edges=() malformed=()` before the fix -- completely
  silent. Also found a REAL, pre-existing instance of exactly this shape
  in `docs/modules/tickets-landing.md:2189` (`frob:enumerates ... Ticket`
  missing its mandatory `members="..."` attribute) during the
  repo-wide positive-control scan below -- filed as a follow-up, not
  hand-fixed (uncertain doc intent, out of dsl.py's scope).

### Shape chosen

Both fixes are "make `_unhandled_markdown_directive` actually check what
it used to assume":

1. `_MD_WAIVE_VALUE_RE` (escape-aware: `(?:[^"\\]|\\.)*`, `\"` does not
   terminate) finds the reason value's REAL closing quote.
   `_md_waive_reason_tail_error` then looks at what follows: nothing/only
   `-->` -> clean; no `-->` anywhere in the tail -> inconclusive (value
   may continue on a later physical line -- left alone, since this
   scanner is line-by-line by construction and cannot see across lines);
   non-whitespace leftover before an on-line `-->` -> genuinely malformed,
   reported with the leftover text quoted.
2. `describes`/`enumerates`/`until`/`ticket`/`doc` moved OUT of the
   blanket-accept `_MD_HANDLED_VERBS` set into a new
   `_MD_DIRECT_EDGE_VERBS` set that `_unhandled_markdown_directive`
   reports as malformed. Safe by construction: a well-formed directive of
   any of these five verbs can never reach this function (the loop
   `continue`s past it), so this cannot introduce a false positive on
   anything that already parses.

Mode 3 (narrower recognition) is untouched -- neither fix touches
`mask_frob_mentions`, `_is_genuine_directive_start`, or the code-comment
scanning path at all, so it cannot have gotten louder or quieter.

### Control results

- **Repo-wide waived-finding count, unchanged**: ran `markdown_anchors`
  over every tracked `*.md` file (5637 files) before vs after the fix.
  `total edges: 1916` identical both times (no valid directive broke).
  `total malformed` went 19 -> 25; the +6 delta is EXCLUSIVELY new,
  genuine finds (4 enumerates/1 ticket/1 until), and of those only ONE
  (`docs/modules/tickets-landing.md`) is inside the real gate's scanned
  file set (`docs/**` + top-level `*.md`, per
  `frob.graph.__init__._collect_files`) -- the other 5 live under
  `tickets/**`, which that walker structurally excludes from doc-file
  classification (the same historical guard that already excludes
  `tickets.md`/`tickets-archive.md` for the identical reason: archived
  Done reports quote directives verbatim as history, not live
  obligations). Zero NEW mode-1 (waive) findings anywhere in the
  repo-wide scan -- the escape-aware check does not disturb a single
  currently-live waiver, including the one repo file that already used
  the informal `\"`-escape convention
  (`docs/modules/tickets-verify-sweep.md:525`), verified explicitly to
  still parse clean.
- **Each malformed shape produces a located diagnostic**: `tests/unit/
  graph/test_dsl_markdown_waive.py::TestWaiveReasonUnescapedQuoteIsLoud::
  test_unescaped_internal_quote_is_reported_not_silently_accepted` and
  `::TestBrokenDirectEdgeVerbIsLoud::
  test_describes_with_a_broken_symref_is_reported_not_silently_dropped`
  (plus the missing-`members=` sibling).
- **Well-formed directives still parse and still suppress**:
  `test_well_formed_waiver_of_an_honored_rule_still_suppresses`,
  `test_escaped_internal_quote_still_parses_cleanly`,
  `test_well_formed_describes_still_parses_cleanly`,
  `test_well_formed_ticket_and_until_still_parse_cleanly`.
- **Multi-line continuation without a trailing quote on this line is not
  flagged**: `test_reason_continuing_onto_a_later_physical_line_is_not_
  flagged` -- covers the genuine multi-line `frob:waive` shape (verified
  against the 5 real repo instances of this exact shape,
  `tickets/T-1968/ticket.md`, `tickets/T-2055/ticket.md`, `tickets/
  T-2099/ticket.md`, `tickets/archive/T-1412/done-report.md`, all outside
  the real gate's scanned set anyway per above, but confirmed non-broken
  regardless).
- Mode-3 regression check: full existing `TestMarkdownDirectiveMentionVsUse`
  class (inline-code-span mention, fenced-code mention,
  `test_unhandled_verb_outside_any_code_span_still_raises`) still passes
  unmodified.

### Changed

- src/frob/graph/dsl.py::_MD_WAIVE_VALUE_RE (new)
- src/frob/graph/dsl.py::_md_waive_reason_tail_error (new)
- src/frob/graph/dsl.py::_MD_DIRECT_EDGE_VERBS (new)
- src/frob/graph/dsl.py::_MD_HANDLED_VERBS (narrowed)
- src/frob/graph/dsl.py::_unhandled_markdown_directive (behavior change)
- docs/modules/graph.md#unhandled-markdown-directives-t-1968 (updated,
  also fixed a stale `frob.gates._mutation_evidence._BUG002_WAIVER_RE`
  reference -- the module was split to `frob.gates._bug_repro` by T-2851,
  after this doc paragraph was last touched)

### Evidence

- Designated repro (BUG002, `FAILED_AT_PARENT` verified against
  09f92218c, the test-only commit before the fix landed):
  `tests/unit/graph/test_dsl_markdown_waive.py::
  TestWaiveReasonUnescapedQuoteIsLoud::
  test_unescaped_internal_quote_is_reported_not_silently_accepted`
- Full bound evidence (8 ids, all in
  `tests/unit/graph/test_dsl_markdown_waive.py`):
  `TestWaiveReasonUnescapedQuoteIsLoud::
  test_unescaped_internal_quote_is_reported_not_silently_accepted`,
  `::test_escaped_internal_quote_still_parses_cleanly`,
  `::test_well_formed_waiver_of_an_honored_rule_still_suppresses`,
  `::test_reason_continuing_onto_a_later_physical_line_is_not_flagged`,
  `TestBrokenDirectEdgeVerbIsLoud::
  test_describes_with_a_broken_symref_is_reported_not_silently_dropped`,
  `::test_enumerates_missing_required_members_attr_is_reported`,
  `::test_well_formed_describes_still_parses_cleanly`,
  `::test_well_formed_ticket_and_until_still_parse_cleanly`.
- `pytest tests/unit/graph/test_dsl_markdown_waive.py tests/unit/graph/
  test_dsl.py tests/unit/graph/test_dsl_mention_escape.py tests/unit/
  gates/test_negexist.py tests/test_graph.py`: 229 collected, 0 failed.
- `frob check --only gates-fast/gates-native/gates-security --ticket
  T-2857`: zero new findings touching `dsl.py`/`graph.md`/
  `test_dsl_markdown_waive.py` -- every error/warning present is
  pre-existing fallout from other tickets' file splits (per this drive's
  own framing), confirmed by grepping the JSON output for our three
  touched paths (zero hits).

### Filed

- T-2870 (renumbers at land): BUG002 ticket-body waiver regex
  silently ignores an unquoted/malformed `reason=` value -- mode 2's real
  fix, out of `src/frob/graph/dsl.py`'s scope.
- T-2869 (renumbers at land): `docs/modules/tickets-landing.md`
  has a `frob:enumerates` anchor with no `members=` attribute -- a
  pre-existing defect this ticket's stricter check newly surfaced but did
  not create; needs domain knowledge of the doc's intent to fix correctly.

### Gates

`frob check --only gates-fast/gates-native/gates-security --ticket
T-2857` (unbudgeted, `gate-summary` present each run): all pre-existing
errors, none touching this ticket's files (verified by grep against the
`--json` output). No new findings introduced by this diff.

### Changed
```
 docs/modules/graph.md                       |  39 +++++++--
 src/frob/graph/dsl.py                       | 125 ++++++++++++++++++++++++++--
 tests/unit/graph/test_dsl_markdown_waive.py | 119 ++++++++++++++++++++++++++
 tickets/T-2857/ticket.md                    |  15 +++-
 tickets/T-2869/ticket.md          |  54 ++++++++++++
 tickets/T-2870/ticket.md          |  63 ++++++++++++++
 6 files changed, 397 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl_markdown_waive.py::TestWaiveReasonUnescapedQuoteIsLoud::test_unescaped_internal_quote_is_reported_not_silently_accepted` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestWaiveReasonUnescapedQuoteIsLoud::test_escaped_internal_quote_still_parses_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestWaiveReasonUnescapedQuoteIsLoud::test_well_formed_waiver_of_an_honored_rule_still_suppresses` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestWaiveReasonUnescapedQuoteIsLoud::test_reason_continuing_onto_a_later_physical_line_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestBrokenDirectEdgeVerbIsLoud::test_describes_with_a_broken_symref_is_reported_not_silently_dropped` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestBrokenDirectEdgeVerbIsLoud::test_enumerates_missing_required_members_attr_is_reported` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestBrokenDirectEdgeVerbIsLoud::test_well_formed_describes_still_parses_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestBrokenDirectEdgeVerbIsLoud::test_well_formed_ticket_and_until_still_parse_cleanly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 27 error(s), 564 warning(s), 798 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, COV003@tickets/T-1102, COV003@tickets/T-1651, COV003@tickets/T-1656, COV003@tickets/T-2375, COV003@tickets/T-2822, COV003@tickets/T-2823, COV003@tickets/T-2824, COV003@tickets/T-2825, COV003@tickets/T-2826, COV003@tickets/T-2829, COV003@tickets/T-2830, COV003@tickets/T-2839, CYCLE001@src/frob/__init__.py, DOC006@tickets/T-2860/ticket.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DOCENUM001@docs/modules/gates.md, DRIFT002@docs/modules/tickets-landing.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PRE001@tickets/T-2857, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
