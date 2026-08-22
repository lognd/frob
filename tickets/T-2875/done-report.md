## Done report

Changed:
src/frob/graph/dsl.py::_RESERVED_MARKER_VERBS
src/frob/process/_reap.py::arm_parent_death_signal
tests/unit/graph/test_dsl.py::TestReservedMarkerVerbs.test_callee_raises_trailing_placement_is_silently_skipped
tests/unit/graph/test_dsl.py::TestReservedMarkerVerbs.test_callee_raises_standalone_placement_is_silently_skipped

Root cause: `_RESERVED_MARKER_VERBS` omitted `"callee-raises"`, on a comment
claiming a same-line trailing `# frob:callee-raises` comment "the DSL's
line-based scan never matches in the first place" -- that claim was false
for both a same-line trailing placement and a standalone full-line
placement of a bare `# frob:callee-raises` comment; both produced a DSL001
unknown-verb `MalformedDirective`. Fixed by adding `"callee-raises"` to the
frozenset with a corrected comment.

Verb-drift question (asked by the ticket): `_RESERVED_MARKER_VERBS` is a
genuinely hand-maintained set, and it WAS drifting -- `"callee-raises"` was
the one missing entry. Full verb inventory taken: every `frob:<verb>`
this repo's code/docs actually emit or document is either (a) routed
through `_VERB_TABLE` (real graph edges), (b) markdown-only
(`generated-start`/`generated-end`/`claims`/`describes`/`enumerates`/
`until`/`ticket`/`doc`/`invariant` -- handled via `_MD_DIRECT_EDGE_VERBS`/
`_MD_HANDLED_VERBS`, never reaching the code-comment `_parse_line` path at
all since they only ever appear as `<!-- frob:x -->` HTML comments), or
(c) an externally-owned code-comment marker routed through
`_RESERVED_MARKER_VERBS`. Category (c) has exactly four members after this
fix: `secret-fake` (frob.gates._secrets), `used-by` (frob.gates._refs),
`raises` (frob.gates._exhaustive_handling), and now `callee-raises`
(frob.arch._python/_ffi, frob.gates._ffi_boundary) -- no other externally-
owned code-comment verb exists in the codebase today (confirmed by
grepping every owning module's own marker literal/regex:
`_REAL_FAKE_MARKER_REASON_RE`, the `"frob:used-by"` prefix check,
`_DIRECTIVE_PREFIX = "# frob:raises "`, `_FROB_RAISES_RE`/
`_CALLEE_RAISES_PRESENT_RE`). No single canonical registry module backs
this set -- each owner keeps its own private literal -- so the duplication
is real, not incidental laziness; deriving it programmatically would mean
a new cross-module coupling out of this ticket's scope. Made the
duplication loud instead: the frozenset's comment now names every owning
module per entry and explicitly states future verb additions must update
this list BY HAND. This repo has a recorded case of exactly this kind of
literal (`_KNOWN_GATE_RULES`) serializing every rule addition until fixed
-- a future ticket may want to derive this one too, but that is a
deliberate architecture decision out of scope for a one-verb bugfix.

`_reap.py` waiver: REMOVED, not re-pointed. T-2874 held a live in-progress
lease on `src/frob/process/_reap.py` for most of this ticket's work; once
that ticket reached state=done, `frob ticket scope T-2875 --add
src/frob/process/_reap.py` succeeded and the now-inert `frob:waive DSL001
follow_up="T-2875"` comment above `libc.prctl(...)` in
`arm_parent_death_signal` was deleted outright, per T-1614's dead-waiver-
debt principle: the fix means the marker has nothing left to suppress, so
re-pointing the waiver at a successor would manufacture follow-up work for
a problem that no longer exists. Verified directly against
`frob.graph.dsl.parse_directives`: `src/frob/process/_reap.py` now parses
with ZERO `MalformedDirective` with the waiver gone -- the DSL001 finding
does not reappear unwaived, confirming the CAUSE is fixed, not merely the
waiver comment deleted. A successor draft (T-2887, "remove the
now-inert waiver...") had been opened earlier, while the lease was still
held; it was dropped with `--absorbed-by T-2875` once the direct removal
made it moot.

Verification (T-2857 bar): ran `frob.graph.dsl.parse_directives`/
`markdown_anchors` over every git-tracked `.py`/`.md` file, before (main)
and after this change. The only `.py`-file entry that changed in the
malformed set is `src/frob/process/_reap.py:183 "unknown verb
'callee-raises'"` -- present before, absent after; every other diff
observed during measurement was a line-number shift from concurrent
unrelated lands on ticket markdown files, not a new or dropped directive.

Positive controls confirmed directly against `parse_directives`:
- valid `# frob:callee-raises` (trailing AND standalone placement) now
  parses with zero `MalformedDirective` (new regression tests).
- an unregistered verb (`frob:not-a-real-verb`) still reports DSL001
  (pre-existing `test_unreserved_unknown_verb_still_reports_malformed`,
  unmodified, still passing).
- the other three pre-existing `_RESERVED_MARKER_VERBS` entries
  (secret-fake/used-by/raises) unaffected: pre-existing tests for them
  still pass unmodified.
- `src/frob/process/_reap.py` itself parses with zero `MalformedDirective`
  after the waiver's removal (the waiver-vs-cause distinction check).

Evidence: tests/unit/graph/test_dsl.py -- 47/47 passed (`SUITE-RESULT:
exitstatus=0 collected=47 failed=0`).

Filed: none. (A successor draft was opened earlier in this ticket's own
work, then dropped in this same change once the direct waiver removal made
it moot -- see the paragraph above; it never became a live open ticket, so
there is nothing outstanding to name here.)

Gates: `frob check --json --ticket T-2875` unbudgeted, gate-summary
present; findings limited to the pre-existing floor other agents own
(COV003, SELFAUDIT001, PERF004, CLAUDE001, TICK004, COV001, DRIFT002,
CYCLE001, DOC011, DOC006, DOCENUM001, a pre-existing DSL001 in
docs/modules/tickets-landing.md unrelated to this diff (verb='enumerates'),
OPAQUE001, PRE001, TICK003, TICK006) -- none in src/frob/graph/dsl.py,
src/frob/process/_reap.py, or tests/unit/graph/test_dsl.py, none
attributed to this diff. `ruff-check` clean on all touched files.

### Changed
```
 rapid-debt.jsonl                   |   1 +
 src/frob/graph/dsl.py              |  30 ++++++++--
 src/frob/process/_reap.py          |   5 --
 tests/unit/graph/test_dsl.py       |  36 +++++++++++
 tickets/T-2875/done-report.md      | 118 +++++++++++++++++++++++++++++++++++++
 tickets/T-2875/ticket.md           |  33 +++++++++++
 tickets/T-2887/ticket.md |  32 ++++++++++
 7 files changed, 245 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl.py::TestReservedMarkerVerbs::test_callee_raises_trailing_placement_is_silently_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestReservedMarkerVerbs::test_callee_raises_standalone_placement_is_silently_skipped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 28 error(s), 514 warning(s), 839 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/claude-hooks.md, DOC006@tickets/T-2879/ticket.md, DOC006@tickets/T-2880/ticket.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT002@docs/modules/tickets-landing.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/ticket_runner/_new.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@src/frob/app/_config_external.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
