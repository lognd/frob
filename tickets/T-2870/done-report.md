## Done report

`_BUG002_WAIVER_RE` (`src/frob/gates/_bug_repro.py`) scans a ticket body's raw text for `frob:waive BUG002 reason="..."` with its own independent regex, entirely outside `frob.graph.dsl`/`parse_directives`/`markdown_anchors` (deliberately -- `tickets.md` is excluded from the general markdown graph walk so a Done report quoting `frob:waive` verbatim never resurrects a phantom edge). Two shapes silently made this regex simply not match, and `_bug002_waiver_reason` treated a non-match identically whether a waiver was never attempted OR an attempt failed to parse: (1) an UNQUOTED `reason=` value (T-2857 mode 2's own measured incident -- the land-time BUG002 check silently did not recognize it, and the land proceeded as though no waiver existed), and (2) a `reason="` opened but never closed anywhere in the rest of the ticket body.

Fix: `_bug002_waiver_reason` itself is unchanged in observable behavior (still returns `None` for both a genuine absence and a malformed attempt) but its underlying regex is now escape-aware (`(?:[^"\\]|\\.)*`, the identical grammar T-2857 already applied to `frob.graph.dsl`'s markdown `frob:waive` regex) so a legitimately escaped `\"` inside a reason value no longer risks truncating early. A new `_bug002_malformed_waiver` function distinguishes the two `None` cases: it looks for a looser `frob:waive BUG002 reason=` shape-match with no corresponding well-formed match at the same position, and `bug_repro_violations` now logs a `WARNING` naming the ticket id and the offending text whenever one is found -- LOUD instead of silent, matching this repo's own dominant-bug-class fix pattern (T-2857/epic T-2391).

Deliberately narrower than T-2857's markdown fix in one respect, documented in both the code comment and docs/modules/gates.md's own BUG002 section update (filed as a follow-up ticket, T-2883, since docs/modules/gates.md was under a concurrent ticket's live scope lease at fix time): does not attempt to tail-check for a genuinely unescaped internal `"` splitting an otherwise-quoted value mid-sentence (T-2857 mode 1's shape) -- a ticket body's `reason="..."` value is free-form prose that legitimately spans multiple lines and parenthetical asides (this repo's own tickets/ already carry several multi-paragraph BUG002 waivers), so there is no `-->`-bounded single physical line to tail-check the way `frob.graph.dsl._md_waive_reason_tail_error` does for markdown without risking a false positive against those live waivers.

Also required narrowing the "shape-like candidate" regex to require `reason=` specifically (not a bare `frob:waive BUG002` mention) after a real repo-wide scan surfaced a genuine false positive: `tickets/T-1748/ticket.md` discusses the mechanism in plain prose ("...plus a frob:waive BUG002 on the second -- both checks disabled...") with no `reason=` attempt and no quoting markup, which T-2218's existing code-span/blockquote exclusion does not cover. Requiring `reason=` specifically resolved it with no loss of detection for the actual measured incident shape.

Verification (the T-2857 bar): wrote a scan script (`/tmp/scan_bug002.py`) that runs `_bug002_waiver_reason`/`_bug002_malformed_waiver` against every `tickets/*/ticket.md` body in this repo. Before this fix's narrowing: 33 well-formed waivers, 1 false-positive malformed (T-1748). After: 33 well-formed (unchanged), 0 malformed -- zero regression against every live BUG002 waiver in the repo, zero false positives. New regression tests (`TestBug002MalformedWaiver`, 6 cases) cover: unquoted value reported, unterminated value reported, well-formed waiver NOT flagged (positive control), no directive at all NOT flagged, bare directive with no reason= attempt NOT flagged (the T-1748 shape), and a malformed EXAMPLE inside a code span NOT flagged (T-2218 precedent). All 69 tests in tests/test_gates_mutation_evidence.py pass.

Filed: T-2883 (docs/modules/gates.md paragraph documenting this diagnostic, deferred only because of a scope-lease conflict with a concurrent ticket at fix time -- narrative already drafted once in this ticket's own history, see the reverted docs/modules/gates.md diff in this worktree's git log for the exact text to restore).

Gates: frob check --json --ticket T-2870 (real run, gate-summary present, unbudgeted): zero new errors attributable to this diff -- the only error-severity findings touching this diff's files are two pre-existing DRIFT002 findings from the unrelated T-2851 file split (docs/modules/tickets-landing.md referencing the old _mutation_evidence.py location). AFFECT001 on bug_repro_violations is waived in-code (frob:waive AFFECT001) with the scope-lease-conflict/deferred-doc-ticket reason recorded above.

### Changed
```
 tickets/T-2870/ticket.md           | 21 ++++++++++++++++++++-
 tickets/T-2883/ticket.md | 29 +++++++++++++++++++++++++++++
 2 files changed, 49 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates_mutation_evidence.py::TestBug002MalformedWaiver::test_unquoted_reason_value_is_reported_not_silently_dropped` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBug002MalformedWaiver::test_unterminated_reason_value_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBug002MalformedWaiver::test_well_formed_waiver_is_not_reported_as_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBug002MalformedWaiver::test_no_directive_at_all_is_not_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBug002MalformedWaiver::test_bare_directive_with_no_reason_attempt_is_not_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBug002MalformedWaiver::test_directive_inside_code_span_is_not_reported` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 15 error(s), 826 warning(s), 839 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/claude-hooks.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DOCENUM001@docs/modules/gates.md, DRIFT002@docs/modules/tickets-landing.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PRE001@tickets/T-2870, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
