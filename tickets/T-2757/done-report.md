## Done report

Changed:
docs/modules/tickets-verify-sweep.md
tests/unit/gates/test_doc011.py

Evidence:
tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_t2757_bare_mention_of_a_deliberately_nonexistent_id_is_flagged
tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_t2757_fix_backtick_quoting_the_second_mention_clears_it

Investigation (two-question protocol, same discipline as T-2745):

1. Does it REPRODUCE? Yes. Direct `_doc011_scan_doc` call and
   `frob check --ticket T-2757` both confirmed it before the fix: line
   1030 of docs/modules/tickets-verify-sweep.md mentioned `T-2736` bare
   (no code span), and DOC011 correctly read it as a real ticket
   citation that must resolve -- it does not (T-2736 never existed;
   that non-existence is literally the incident the doc is documenting).

2. Is the BLAME right? No. `git show --stat 79c9e4a436` (T-2741, the
   land the sweep says spawned it) touched only PII-gate files,
   CHANGELOG, and its own ticket -- never this doc. Attribution
   correctly said UNATTRIBUTED. The actual introducing commit is
   2dc7202bc (T-2744, "Quarantine was cleared citing an auto-filed
   ticket that does not exist"), landed 31 minutes EARLIER on the same
   day: T-2744 added this whole doc section describing the T-2736
   incident, and in doing so introduced a bare mention of the very
   phantom id its own fix was about -- self-inflicted drift from an
   ancestor land, not from the land the sweep happened to be spawned by.

Root cause: the doc mentions `T-2736` TWICE. The first mention (a
multi-line inline code span: `` `cleared_reason: ... as\nT-2736` ``)
correctly illustrates the literal string and DOC011 exempts it, same as
the `test_id_inside_inline_code_span_is_not_flagged` precedent. The
second mention ("the direct fix for the T-2736 mechanism specifically")
was left bare -- an inconsistency within the same doc, not a typo'd or
stale id. Fix: backtick-quote the second mention too, matching the
first's style.

Root-cause grouping: same class of defect as T-1542 (a genuinely
non-existent id cited for illustrative purposes needs a code span, not
bare prose) -- extended the EXISTING tests/unit/gates/test_doc011.py
(which already carries the T-1542 precedent tests) with two new cases
covering this specific bare-vs-code-span recurrence, rather than a
one-off untested edit.

BUG002: waived via frob:waive BUG002 in T-2757's own body (T-1616
escape-hatch precedent, same posture as T-2745) -- the fix is pure doc
prose (backtick placement), not a code change, so no designated test can
genuinely fail-at-parent/pass-at-fix; DOC011's gate LOGIC is unchanged,
only doc DATA changed. The two added tests instead prove the gate logic
itself against both shapes.

Filed: none. No out-of-scope work found.

Gates: frob check --ticket T-2757 clean on both touched files (0
diagnostics of any severity, confirmed via direct JSON filter, not a
grep pipeline). Pre-existing repo-wide WAIVE/EXHAUST003/etc. warnings
present in the scoped run are unrelated debt, not introduced by this
change. frob:waive BUG002 recorded per above (a documented escape hatch,
not a waived gate finding).

### Changed
```
 tests/unit/gates/test_doc011.py | 53 +++++++++++++++++++++++++++++++++++++++++
 1 file changed, 53 insertions(+)
```

### Evidence
- `tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_t2757_bare_mention_of_a_deliberately_nonexistent_id_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_t2757_fix_backtick_quoting_the_second_mention_clears_it` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 18 error(s), 912 warning(s), 707 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, PRE001@tickets/T-2757, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
