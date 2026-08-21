## Done report

Re-verified this WIRE001 follow_up anchor after T-2746 (WIRE001's new
property/attribute-access tracing, `_is_property`/`_PROPERTY_DECORATOR_
RE`/`property_access_pattern` in src/frob/gates/_wire.py). That extension
covers an `@property`-decorated method read via attribute syntax; it does
not touch how the callgraph traces a class passed as a `formatter_class=`
constructor kwarg and invoked internally by argparse's own help-rendering
machinery, which lives entirely in the argparse stdlib, out of repo, and
out of reach of the best-effort callgraph regardless of this extension.
Disposition unchanged: (b) genuine blind spot, not detector-fixable.

The three waivers in src/frob/__main__.py (lines 244, 264, 281) already
state the mechanism, not just the rule name: `_GroupedHelpFormatter` is
passed as `formatter_class=_GroupedHelpFormatter` to the root argparse
parser, and its `_format_action`/`_format_grouped_subparsers` methods are
invoked internally by argparse's own formatter protocol during help
rendering -- never called directly by name from this repo's own code.

Positive control, both directions, measured directly:
1. `frob check --only gates --no-cache` over the whole repo: zero WIRE001
   findings in src/frob/__main__.py -- the existing waivers hold.
2. Planted `_t1831_planted_dead_control` (a genuinely dead function, no
   caller anywhere) at the end of src/frob/__main__.py, re-ran the same
   check: WIRE001 fired on it immediately (`src/frob/__main__.py:771
   WIRE001: ... is new in this diff and has no caller`). Confirms the
   gate is not blinded on this file -- removed the plant before landing,
   tree is clean.

No code change: the waivers and anchor metadata are already correct on
main. This ticket stays anchor=True/queued forever (T-1856): WIRE002
requires a real, non-terminal ticket id as follow_up, and closing this
ticket would orphan the three citations in src/frob/__main__.py.

Filed: none.

### Changed
```
 rapid-debt.jsonl              |  1 +
 tickets/T-1831/ticket.md      |  2 +-
 tickets/T-2451/done-report.md | 52 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2451/ticket.md      |  9 +++++++-
 4 files changed, 62 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 18 error(s), 837 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
