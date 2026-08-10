## Done report

MEASURED FLOOR: 105 errors (frob check --only gates) immediately after
T-1970/T-1968 both landed, confirmed by re-running from a fresh worktree
off that exact main tip before touching anything. 104 of 105 fixed; 1
residual (CHANGELOG.md:1853) is structurally unreachable from any
worktree -- see T-1994 (renumbers at land).

TRIAGE SPLIT (105 total), verified per-finding, not bulk-applied:

(1) WIRED AS REAL EDGES -- genuine directives with a confirmed reader
    that _MD_HANDLED_VERBS/markdown_anchors simply never recognized:
      invariant (43) -- frob.gates._inv._DOC_INVARIANT_MARKER_RE already
        reads <!-- frob:invariant INV-### --> for INV003/INV004.
      claims (1) -- frob.gates._sys._CLAIMS_RE already reads
        <!-- frob:claims <view> --> for DOC003.
      used-by (1) -- frob.gates._refs already reads frob:used-by via its
        own raw-text scan (REF001/REF002/REF003), already carved out for
        code comments via _RESERVED_MARKER_VERBS but never folded into
        markdown's separate handled-verb set.
      ticket (35) -- new: <!-- frob:ticket T-#### --> is a consistent,
        well-formed doc-authoring convention (docs/strata/*.md and
        others) with no prior reader. Added a markdown-side TICKET edge
        (_TICKET_MD_RE, mirrors _UNTIL_RE exactly).
      doc (18) -- new: <!-- frob:doc <target> --> is a self-anchor
        convention, 16/18 well-formed (target matches a real heading
        slug in the same file), 2 malformed (see (3) below). Added a
        markdown-side DOC edge (_DOC_MD_RE).

(2) MENTIONS -- doc prose quoting a directive as a worked example inside
    markdown's own code-span syntax, not a live directive:
      <verb> (2, docs/modules/graph.md) -- DSL grammar reference table.
      tests (1, docs/modules/arch.md) -- converted to plain prose (the
        directive-shaped line added nothing the following sentence
        didn't already say).
      waive malformed-shape (3 of 4: docs/modules/graph.md,
        docs/modules/gates.md, CHANGELOG.md) -- worked examples inside
        backticks. GENERAL FIX (not per-site quoting): markdown_anchors
        now blanks fenced/inline code spans before directive matching
        (_blank_code_spans), same earliest-insertion-point pattern
        T-1970's mask_frob_mentions established -- deliberately SAME-LINE
        inline spans only (a whole-file multi-line regex was tried and
        measured unsafe: docs/modules/gates.md alone carries an ODD total
        backtick count, 7657, so file-wide non-greedy pairing mispairs
        past the first stray backtick). The two doc-owned multi-line
        examples (graph.md, gates.md) were rewrapped onto one line so the
        safe same-line detector catches them; CHANGELOG.md's could not be
        (land-owned, T-1994).

(3) GENUINE BUT UNREAD, FIXED OR REMOVED (the finding doing its job):
      waive SCOPE001 (1, docs/guides/install.md) -- a real, well-formed
        <!-- frob:waive SCOPE001 reason="..." --> naming a rule with NO
        markdown-reading mechanism anywhere (verified: SCOPE001 is a
        diff/lease-scope gate, never markdown-text-scanned). Removed --
        it suppressed nothing and its own reason cited a stale T-0241 bug.
      frob:doc target mismatches (2 of the 18 doc-verb sites, surfaced
        AFTER wiring frob:doc into a real, resolution-checked edge):
        docs/design/coding-performance-corpus.md and
        docs/design/language-adapter-tier-decision.md self-declared
        anchor slugs that did not match any real heading in the file.
        Corrected both to the real heading's slugify() output.
      frob:doc wrong-direction targets (2 more of the 18): 
        docs/design/design-pattern-traps-corpus.md and
        docs/design/system-performance-corpus.md pointed frob:doc at a
        bare src/ DIRECTORY, not a doc anchor -- a different, ambiguous
        usage from the other 16 self-anchor sites. Removed rather than
        guessed at new edge semantics for a 2-site pattern; the doc's own
        title/prose already conveys the topic-area relationance.

SAFETY CHECK the coordinator asked for: did any of the 105 turn out to
be a REAL directive nothing reads, that this fix could have silently
re-hidden by treating it as a mention? Yes, exactly one -- SCOPE001 in
install.md -- and it was NOT wrapped or blanked; it was individually
inspected, confirmed to have no reader, and removed per (3), never
folded into the generic (2) code-span masking.

NEW ACCEPTANCE TESTS (tests/unit/graph/test_dsl_markdown_waive.py::
TestMarkdownDirectiveMentionVsUse), written to fail before the fix and
pass after: test_unhandled_verb_inside_inline_code_span_is_a_mention_
not_a_finding (mention, no finding) and test_unhandled_verb_outside_
any_code_span_still_raises (same rule/verb, no backticks, still raises)
-- proving the fix discriminates by code-span membership, not a blanket
DSL001 downgrade.

frob:waive BUG002 reason="all evidence exercises brand-new code (_blank_code_spans, the markdown TICKET/DOC edge production, _MD_HANDLED_VERBS additions) added in this same ticket's diff -- every bound test node is a NEW test that cannot COLLECT at the parent commit (NO_VERDICT, exit 5, per docs/guides/agent-playbook.md's T-1929 structural exception: a brand-new test node has no parent-commit form to fail against, not a confirmatory-only evasion). Verified via frob ticket evidence T-1989 --check-repro on the strongest candidate (TestMarkdownDirectiveMentionVsUse::test_unhandled_verb_inside_inline_code_span_is_a_mention_not_a_finding): NO_VERDICT, could not collect at 9bf10bd14aab8c1a4fdddc8a10d6032064e4678d."

### Changed
```
 tickets/T-1989/done-report.md      |  98 +++++++++++++++++
 tickets/T-1989/ticket.md           | 214 ++++++++++++++++++++++++++++++++++++-
 tickets/T-1994/ticket.md |  53 +++++++++
 3 files changed, 363 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_waive_of_a_genuinely_unhonored_rule_is_reported_unparsed` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_waive_of_each_honored_rule_produces_no_finding` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_multiple_unhonored_waivers_each_reported` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_recognized_verbs_produce_no_unhandled_finding` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_unknown_verb_entirely_is_reported` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestMarkdownDirectiveMentionVsUse::test_unhandled_verb_inside_inline_code_span_is_a_mention_not_a_finding` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestMarkdownDirectiveMentionVsUse::test_unhandled_verb_outside_any_code_span_still_raises` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestMarkdownDirectiveMentionVsUse::test_unhandled_verb_inside_fenced_code_block_is_also_a_mention` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestMarkdownDirectiveMentionVsUse::test_ticket_directive_in_markdown_produces_a_ticket_edge` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_markdown_waive.py::TestMarkdownDirectiveMentionVsUse::test_doc_directive_in_markdown_produces_a_doc_edge` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/t1989-only/tests/unit/test_tickets_evidence_only_scope.py
