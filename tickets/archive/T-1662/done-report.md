## Done report

Epic closure record for T-1662 ("every check must decide from semantics,
never a lexical match"), appended as a new "Epic closure" section to
docs/design/gate-semantics-classification.md rather than a bare state
flip -- this is the record someone reads in six months to know what the
directive actually meant here.

DENOMINATOR (from T-1663's classification pass, already recorded in this
doc's tables): the large majority of rule families were already class
(a), fully semantic (COV, DRIFT, AFFECT, SCOPE, SUPPRESS, PRE, INV, TEST,
BUG002, TODO, DEBT, DEPR, DSL001, WAIVE, DEC, REL, DOC link/anchor/
pointer families, DUP, FUZZ, PERF, VET, SYS, NATIVE001, TICK
state-machine half, FFI, RENDER001). A small named set is class (b),
legitimately lexical with a stated reason (SEC001-004, EXCL001, `frob
fmt`'s directive-wrap reflow, `_rule_id_scan.py`'s own rule-id-literal
generator, TICK011's disclosure trigger phrase-scan, WAIVE004's
directive-parsing half).

CLASS (c), lexical and wrong -- 7 confirmed, all fixed:
1. REF001 (T-1665)
2. DEAD001/OPAQUE001 symref gap (filed T-1683, superseded by the more
   direct T-1652/T-1659 symref fixes landing the same guarantee first)
3. DEBT/DEPR `_looks_like_call` regex-over-raw-lines (T-2178)
4. callgraph substrate bare-short-name resolution, no import
   verification (T-2188)
5. `walk_strata` parse-then-discard, re-deriving by line regex what the
   grammar-parsed tree already had (T-2187)
6. Pre-land directive substring gate over diff text (T-2201)
7. TICK006 prose-as-declaration, a citation-shaped phrase in Done-report
   narrative read as a real ticket citation (T-2243)

WALK001 was investigated per the ticket's own shortlist and RECLASSIFIED
OUT of the defect set -- direct inspection found it already AST-based and
import-alias-aware; its one real gap (attribute-name matching without
type info) is the same accepted RENDER001-shaped limitation, not a
text-match defect. Recorded in the doc so it is not re-filed against this
epic expecting a different verdict.

THE EPIC'S ACTUAL DELIVERABLE: directive #4's meta-check, T-2344's
LEXCHECK001 (src/frob/gates/_lexical_selfcheck.py) -- an AST scan of
src/frob/gates/** flagging any function that both regex-decides and
constructs a symref-less Violation, the exact shared shape of every
instance above. On its FIRST real run against this repo it found 8
candidates: 6 were genuinely class (b) and allowlisted with stated
reasons; the 8th, `_wire001_cli_dest_violations` (WIRE001 case 3), was a
real, unresolved class-(c) instance -- and was NOT silently allowlisted.
It was waived in-file with an explicit follow_up="T-2348" citation and a
real ticket filed. T-2348 (this session) raised it to a parsed decision
against `_config_external.py`'s AST-collected forwarded-field set and
removed the waiver. This is the guard proving itself on day zero: it
caught a real pre-existing defect the classification survey itself never
saw, precisely because it checks the CODE, not a one-time human pass.

CLOSURE CRITERION MET, verified directly before writing this report:
- `frob check --only lexcheck` measures zero LEXCHECK001 findings on the
  real repo (confirmed in this worktree just now: gate:LEXCHECK does not
  even appear in the failing tool summary -- 0 findings).
- `grep LEXCHECK001 src/frob/gates/_wire.py` returns nothing -- no
  in-file waiver remains.
- Every ticket ever filed with `parent: T-1662` (T-1663, T-1664, T-1665)
  is `done`; every follow-on deliverable ticket (T-2178, T-2201, T-2187,
  T-2188, T-2243, T-2344, T-2348) is `done`, each verified individually
  via `frob ticket show`.

No open ticket anywhere in tickets.md traces back to this epic.

### Changed
```
 docs/design/gate-semantics-classification.md | 93 ++++++++++++++++++++++++++++
 tickets/T-1662/ticket.md                     |  6 +-
 2 files changed, 98 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1662/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-1662, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
