## Done report

WIRE001 case 3 (`_wire001_cli_dest_violations`, src/frob/gates/_wire.py)
decided "is this new CLI dest= wired into _config_external.py" via a raw
substring-membership scan over that file's text -- the last known,
self-admitted class-(c) lexical decider LEXCHECK001 (T-2344) found and
this ticket's own body names.

Fix: added `_config_external_forwarded_dest_names`, which AST-parses
`_config_external.py` and collects every string literal element of a
module-level tuple/list/set/frozenset(...) assignment -- the same
PARSED surface T-2004's `_all_forwarded_field_names` computes at
runtime, read from source text here instead so this gate module needs
no import of (or dependency cycle onto) frob.app._config_external.
`_wire001_cli_dest_violations` now decides membership against that
parsed set. A dest string that merely appears in a comment or
docstring no longer reads as "wired" (the false-negative direction the
old scan had); a dest genuinely wired only through a tuple structure
still reads as wired (positive control); a dest not wired anywhere
still fires WIRE001 (baseline real-catch case).

Also split the diff-added-line dest-literal extraction into its own
function (`_cli_dest_literals_in_added_lines`) so no single function
both calls a regex AND constructs a symref-less Violation -- the
LEXCHECK001 meta-check's own per-function detection shape. Removed the
in-file `frob:waive LEXCHECK001 ... follow_up="T-2348"` waiver along
with the fix, per the ticket's own instruction not to leave it behind.

Verified against the real checkout: `frob check --only lexcheck --only
wire` no longer reports LEXCHECK001 for this function at all (was 1
waived finding before the fix, 0 findings of any kind after).
`tests/unit/gates/test_lexical_selfcheck.py`'s repo-wide raw-finding-set
assertion was updated from "exactly _wire.py" to "empty" to match.

Also updated: `tests/unit/gates/test_lexical_selfcheck.py`'s
`test_every_known_gates_module_module_stays_clean` (scope widened via
`frob ticket scope --add` since the fix changes what that test's own
assertion must be), and added
`tests/unit/gates/test_wire001_cli_dest_semantic.py` (new file) with
the positive controls above.

### Changed
```
 src/frob/gates/_wire.py                            | 140 +++++++++++++++------
 tests/unit/gates/test_lexical_selfcheck.py         |  22 ++--
 tests/unit/gates/test_wire001_cli_dest_semantic.py | 135 ++++++++++++++++++++
 tickets/T-2348/ticket.md                           |  24 +++-
 4 files changed, 272 insertions(+), 49 deletions(-)
```

### Evidence
- `tests/unit/gates/test_wire001_cli_dest_semantic.py::TestConfigExternalForwardedDestNames::test_collects_tuple_and_frozenset_literals` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_wire001_cli_dest_semantic.py::TestConfigExternalForwardedDestNames::test_comment_and_docstring_mentions_are_not_collected` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_wire001_cli_dest_semantic.py::TestConfigExternalForwardedDestNames::test_unparseable_text_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_wire001_cli_dest_semantic.py::TestWire001CliDestViolations::test_dest_wired_only_through_tuple_structure_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_wire001_cli_dest_semantic.py::TestWire001CliDestViolations::test_dest_mentioned_only_in_a_comment_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_wire001_cli_dest_semantic.py::TestWire001CliDestViolations::test_dest_not_wired_at_all_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_every_known_gates_module_module_stays_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2348/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2348, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
