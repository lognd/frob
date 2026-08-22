## Done report

Changed:
tickets/T-2742/ticket.md
tests/unit/test_ticket_2691_doc006.py

Evidence:
tests/unit/test_ticket_2691_doc006.py::TestTicket2742Doc006Regression::test_backticked_future_verb_is_flagged
tests/unit/test_ticket_2691_doc006.py::TestTicket2742Doc006Regression::test_prose_description_of_future_verb_not_flagged

Investigation (per dispatch brief's two-question protocol):

1. Does it REPRODUCE? Yes. Confirmed by direct doc006_gate call and by
   frob check --ticket T-2745 both before and after: T-2742's body
   backtick-quoted a two-word phrase, `frob land status`, in the exact
   shape DOC006 reads as a live CLI invocation that must resolve against
   the argparse dispatch table -- it does not (no such verb exists),
   so DOC006 correctly fired. This is the identical mistake T-2697 fixed
   once already on T-2691's body three days earlier (see
   tests/unit/test_ticket_2691_doc006.py, pre-existing file).

2. Is the BLAME right? No, and this is expected, not a bug in
   attribution: `git show --stat 802534a13ec` (the blamed land, T-2712)
   touched only PII gate files, CHANGELOG, and T-2712/T-2741 tickets --
   it never touched tickets/T-2742/ticket.md. Attribution correctly
   reported UNATTRIBUTED. The real cause is T-2742's own body_changes
   log: two `logan` actor appends on 2026-08-20, the second one literally
   titled "record why this ticket tripped DOC006" -- i.e. the ticket's
   own prose introduced the drift the sweep detected; the sweep just
   happened to be spawned by an unrelated land at the time it ran.

Fix: reworded the backtick-quoted hypothetical verb as plain prose (same
remedy T-2697 used for T-2691), so DOC006 no longer reads it as a real,
must-resolve CLI invocation:

  before: `frob land status`
  after:  a hypothetical "frob land status" verb (not a real command;
          do not run it)

Verified DOC006 no longer fires against the fixed file: direct
doc006_gate() call over the real repo tree returned 0 matches for
tickets/T-2742/ticket.md (509 pre-existing repo-wide DOC006 findings
elsewhere, untouched by this ticket); frob check --ticket T-2745 --json
--no-cache confirms no diagnostic of any severity on either touched file.

Root-cause grouping: this is the SAME root cause as T-2691/T-2697 (a
hypothetical future CLI verb written in backticks), recurring on a
different ticket. Rather than a one-off edit, extended the existing
regression-test file (tests/unit/test_ticket_2691_doc006.py) with a new
TestTicket2742Doc006Regression class mirroring its established pattern,
so the specific recurrence is now covered by an executable test alongside
T-2691's.

BUG002: waived via frob:waive BUG002 in T-2745's own body (T-1616
escape-hatch precedent) -- the fix is pure ticket-body prose, not a code
change, so no designated test can genuinely fail-at-parent/pass-at-fix
(DOC006's gate LOGIC is unchanged; only ticket-file DATA changed). The
two added tests instead prove the gate logic itself: the pre-fix shape is
flagged, the post-fix shape is not -- same evidence class T-2697 used.

Filed: none. No out-of-scope work found; T-2742 itself (the ticket whose
body was fixed) is separate, pre-existing, unrelated work already queued.

Gates: frob check --ticket T-2745 clean on both touched files (0
diagnostics of any severity); 31 pre-existing repo-wide errors present in
the scoped run are unrelated debt (COV/DRIFT/ARCH/TICK/PII/SEC families,
none touching T-2742/ticket.md or the new test file) -- not introduced by
this change, not waived, out of scope for this ticket. frob:waive BUG002
recorded per above (not a waived gate finding, the BUG002 mutation-
evidence check itself, per T-1616's documented escape hatch).

Note: `frob test --base main` fell back to a full-package pytest run
(ticket .md files are "unbound" symbols, triggering the documented
package-fallback) rather than a touched-set run; per dispatch
instructions the full suite was not run/awaited for this ticket's
verification. The two designated evidence tests were run directly and
pass (5/5 in the full test_ticket_2691_doc006.py file, 2/2 new).

### Changed
```
 tickets/T-2745/ticket.md | 28 ++++++++++++++++++++++++++--
 1 file changed, 26 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_2691_doc006.py::TestTicket2742Doc006Regression::test_backticked_future_verb_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_2691_doc006.py::TestTicket2742Doc006Regression::test_prose_description_of_future_verb_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 21 error(s), 992 warning(s), 705 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC011@docs/modules/tickets-verify-sweep.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, PII012@src/frob/serve/_socketd.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2745, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
