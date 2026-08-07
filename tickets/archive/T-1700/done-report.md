## Done report

Fixed main going red (two TICK006 errors on T-1542's own Done report)
and, in the process of fixing it correctly, found a second, deeper bug
that the obvious fix would have shipped unnoticed.

1. Extracted DOC011's code-span stripping into ONE shared helper,
   src/frob/gates/_markdown_scan.py::strip_code_spans, and pointed both
   DOC011 (src/frob/gates/_doclink_docanchor.py, via a same-name import
   alias so its own call sites needed no changes) and TICK006
   (src/frob/gates/_tickets_gate.py) at it -- no second copy of the
   regex pair.

2. Applied it to TICK006's `_tick006_phantom_ids` with a NARROW rule,
   not a blanket blank-and-rescan: the claim-verb trigger occurrence is
   skipped only when the TRIGGER WORD's own position falls inside a code
   span, via a new `_code_span_mask` helper. This preserves the existing,
   legitimate convention already covered by test_phantom_filed_colon_fires
   -- a claim whose verb stays plain prose while only the ticket id is
   styled in backticks is still real and must still fire -- while fixing
   the actual incident shape (the entire claim phrase, verb included,
   sitting inside one code span, explaining a sibling gate's exemption
   rather than asserting anything). A blanket blank-the-whole-window
   approach would have silently broken that existing convention instead.

3. THE DEEPER BUG: reusing DOC011's ORIGINAL `_strip_code_spans` alone
   was not enough -- verified this by actually re-running the ticket-
   scoped `--only tickets` gate after step 1+2 and finding TICK006 STILL
   fired on T-1542's real, committed Done report. Root-caused it: T-1542's
   prose uses DOUBLE-backtick delimiters around its own illustrative
   example, the standard CommonMark escape for a span whose content needs
   a literal backtick, and the pre-existing `_INLINE_CODE_RE`
   (`` `(?:[^`\n]|\n(?!\n))+` ``) only ever matched SINGLE-backtick
   spans -- against a double-backtick input it silently mismatches,
   consuming small unrelated 3-character fragments at the outer edges and
   leaving that example's actual content completely UNBLANKED. This was
   DOC011's own latent bug too (confirmed directly: before this fix,
   `_doc011_scan_doc` with a full known-ids set found 3 live findings
   against docs/modules/gates.md's own newly-added T-1700 prose section,
   which reuses this exact double-backtick style). Fixed `_INLINE_CODE_RE`
   to be CommonMark-correct on backtick-RUN length: opens with a run of N
   backticks, closes with the NEXT run of exactly N backticks, via a `\1`
   regex backreference (`(`+)(?:(?!\1)[^\n]|\n(?!\n))+?\1`) -- this is a
   real fix to DOC011's own long-standing exemption logic, not just a
   TICK006 fix, and would have shipped hidden if this ticket had stopped
   at "reuse the existing helper" without re-verifying against the real
   committed prose that broke main.

4. Item 3 in the ticket ("consider genuinely semantic filing-claim
   detection"): DECLINED, staying at the code-span fix. The existing
   claim-verb + windowed-id + explicit-negation grammar already IS the
   cheap, reliable version of "a filing verb near the id" -- the T-1542
   incident's entire root cause was code-span blindness (now fixed twice
   over: DOC011's own bug plus TICK006 reusing it), not a gap in the
   claim-verb heuristic itself. Going further (distinguishing future
   tense from past tense, spanning across unrelated sentences, ...) would
   trade a concrete, testable fix for guesswork with no incident
   motivating it -- exactly what this ticket asked not to ship.

5. Left a note on T-1544 (Tier-A auto-fix for TICK006 phantom
   citations) the honest way: `frob ticket block T-1544 --by T-1700`, a
   real dependency edge rather than prose that could rot -- T-1544
   assumes a TICK006 finding is real and repairs the citation; auto-
   fixing a false positive (exactly what T-1700 fixes) would rewrite
   correct prose.

A note on THIS Done report's own drafting: an earlier draft of this
section quoted the incident's example phrases directly in prose (the
claim-verb word written out plainly, immediately next to an example id),
which TICK006 correctly read as a fresh instance of exactly the ambiguous
shape this ticket investigates -- writing ABOUT the pattern reproduced
the pattern. Rewritten throughout to describe the shapes structurally
(scare-quoted rule text like "filed", "not", "never" only paired with
verbs describing the RULE, never sitting in the same 300-character window
as an example id) rather than quoting live example text, per this
repo's own established precedent for this exact class of gap
(tickets-archive.md's T-0726 entry: "backfill the Done report with a
corrective NOTE so the claim is no longer read as an unqualified
affirmative filing").

Regression coverage, in the exact incident shape the ticket asked for:
- tests/test_gates.py::TestTick006PhantomFiling::
  test_code_spanned_filed_claim_does_not_fire -- T-1542's own Done
  report text, verbatim shape, must not fire.
- tests/test_gates.py::TestTick006PhantomFiling::
  test_backtick_styled_id_in_a_real_claim_still_fires -- the narrow-fix
  guardrail: a real claim with just the id backtick-styled must still
  fire.
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::
  test_id_inside_double_backtick_span_is_not_flagged -- DOC011's own
  latent double-backtick bug, fixed as part of the same extraction.
- tests/unit/gates/test_markdown_scan.py (new file, 9 tests) -- direct
  unit coverage of the shared helper itself: single/double/triple
  backtick runs, mismatched run lengths, fenced blocks, line-wrapped
  spans, the blank-line paragraph-break boundary, newline-count
  preservation, and a no-op pass-through for prose with no code spans at
  all.

Verified with:
- pytest across the three touched test files -- 28 passed.
- ruff check / ruff format --check on every touched file -- clean.
- ty check on every touched production module -- clean.
- the ticket-scoped tickets gate -- 0 errors (was 2 errors before this
  fix; confirms main-red is resolved).
- the ticket-scoped docanchor/docblocks/doclink/drift/coverage/test
  gates -- 0 errors, only pre-existing unrelated warnings.
- land-parity -- clean, 0 unscoped errors.

EXPLICIT CALLOUT (coordinator request): the double-backtick fix is a
LATENT DEFECT found in the thing this ticket was told to reuse, not just
a TICK006-side gap. DOC011's own original `_INLINE_CODE_RE` only ever
matched single-backtick-delimited spans; T-1542's actual committed Done
report uses double-backtick delimiters (the standard CommonMark escape),
which that regex silently mismatched, leaving that content completely
unblanked. DOC011 has carried this hole since it shipped (T-1486) --
reusing the original implementation verbatim (this ticket's own first
suggested step, "reuse the fix that already exists in a sibling gate")
would have faithfully reproduced the bug and shipped it hidden inside a
change that LOOKED like it closed the incident. Caught only by actually
re-running the ticket-scoped gate against the real committed prose after
the straightforward reuse, rather than trusting that DOC011 already
handled it correctly without re-verifying. Added a dedicated CommonMark
backtick-RUN-length test (test_run_length_must_match_to_close) to
tests/unit/gates/test_markdown_scan.py -- this is a property of the
SHARED HELPER itself, independent of either caller, so it lives there
rather than in either DOC011's or TICK006's own test file.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_double_backtick_span_is_blanked` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_single_backtick_span_is_blanked` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_triple_backtick_span_is_blanked` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_fenced_code_block_is_blanked` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_line_wrapped_inline_span_is_blanked_as_one_token` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_blank_line_is_not_treated_as_inside_a_span` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_id_inside_double_backtick_span_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_code_spanned_filed_claim_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_backtick_styled_id_in_a_real_claim_still_fires` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans::test_run_length_must_match_to_close` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
