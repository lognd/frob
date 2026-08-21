## Done report

Confirmed the false positive live: `frob worktree sweep --force` (real, T-1739,
`frob.app.worktree_runner._build_worktree_parser`) was missing from
`_build_parser()`'s decorative `--help`-only mirror
(`frob._cli_parsers._core._add_worktree_parser`, which only registered
path/--dry-run/--min-age), so DOC006's flag-resolution path
(`_leaf_parser`/`_cli_violations`) flagged the one live doc citing it.

Fix mirrors T-2533's own shape exactly, reusing its `_BYPASS_SUBTREE_PATCHES`
table (`frob.gates._docblocks_refs`) rather than building a second one:
`_leaf_parser` now checks, at each chain hop, whether `(parser_dotted, word)`
is a known dispatch bypass; if so it swaps in the REAL dispatch-time parser
object (built via `_load_parser_factory`) before continuing the walk and
reading `--flag` names off it, instead of the mirror's own (possibly
incomplete) `_option_string_actions`. `_cli_violations` now passes
`parser_dotted=source.parser` through.

Removed the one `frob:waive DOC006` this ticket's own filing added at
docs/modules/tickets-landing.md's "worktree sweep --force" mention, now that
the false positive it covered no longer fires.

POSITIVE CONTROLS, BOTH DIRECTIONS (mandatory per this ticket's kind):
- `test_dispatch_bypassed_worktree_sweep_force_flag_not_flagged`: the real
  `--force` flag on the bypassed `worktree sweep` parser is no longer
  flagged.
- `test_worktree_sweep_nonexistent_flag_still_flagged`: a genuinely
  nonexistent flag on that SAME bypassed parser still fires -- proves the
  patch is not a blanket "trust anything under worktree sweep" widening,
  the failure mode the ticket itself named.

Both run green; the pre-existing `tests/test_docptr_gate.py::
TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo`
still fails, unrelated: one DOC006 finding on
docs/audits/test005-zero-classification-t1418.md (a broken heading anchor
into docs/guides/agent-playbook.md), outside this ticket's scope, present
before and after this change.

Fixed two ticket-scoped gate findings the new tests introduced: COV002
(added a `frob:ticket T-2559` edge on `TestDoc006Cli`, whose body the new
methods changed) and DUP001 (the new worktree-sweep-force fixture is
100% structurally similar to T-2533's own sibling positive fixtures by
deliberate design -- same _init_repo/_write/_add_all/doc006_gate shape,
different literal doc text per case -- waived with that reason rather than
extracted, since extracting would obscure each case's own doc text, the
actual thing under test). Also fixed a malformed multi-line frob:waive
directive (continuation lines need the `#` prefix repeated, per this
repo's own `_coverage_sites.py` WIRE001 convention) caught by `frob ticket
sweep`'s own directive-parse warning before it could ship broken.

Scope extended (frob ticket scope --add) from the ticket's original
src/frob/gates/_docptr.py-only declaration to also cover
tests/test_docptr_gate.py and docs/modules/tickets-landing.md, since the
ticket's own brief requires both the positive-control tests and removing
the waiver.

### Changed
```
 docs/modules/tickets-landing.md |  2 +-
 src/frob/gates/_docptr.py       | 45 +++++++++++++++++++++++++++++++---
 tests/test_docptr_gate.py       | 53 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-2558/ticket.md        |  6 +++++
 tickets/T-2559/ticket.md        | 25 ++++++++++++++++++-
 tickets/T-2589/ticket.md        |  8 ++++++-
 tickets/T-2600/ticket.md        |  5 ++++
 7 files changed, 138 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006Cli::test_dispatch_bypassed_worktree_sweep_force_flag_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Cli::test_worktree_sweep_nonexistent_flag_still_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 20 error(s), 914 warning(s), 709 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, E501@/home/logan/projects/frob/.claude/worktrees/fa-t2589-t2559/src/frob/tickets/_new_renumber.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2559, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
