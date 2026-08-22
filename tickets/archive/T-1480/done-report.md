## Done report

Built `frob sys trace <from> [to]` (T-1480), the influence-closure
witness-path CLI wrapper over the already-shipped `FactBase.reachable`.

The prior attempt (Failure log, 2026-08-08) found this ticket undoable as
declared-scoped: the parser registration point (`_add_sys_parser` in
`src/frob/_cli_parsers/_misc.py`) sat outside both the declared scope and
the FEATURE-kind CLI_WIRING_FILES implicit grant (T-0446/T-1848, which
covers only `__main__.py`/`app/config.py`/`app/ticket_runner/__init__.py`,
not individual `_cli_parsers/**` modules per that constant's own T-1848
comment). Re-verified this was still true, confirmed no other in-progress
ticket currently holds `src/frob/_cli_parsers/_misc.py` (checked every
live worktree's dirty/committed state), and used the sanctioned,
audited mechanism the same comment names for exactly this situation:
`frob ticket scope T-1480 --add src/frob/_cli_parsers/_misc.py --reason
...` -- not a silent expansion.

Built only `trace`, the one verb the prior investigation found cheaply
buildable (a thin wrapper, no new detection logic). Left `check`/
`capacity`/`threats` as disclosed cuts with filed residue tickets, per
that same investigation's conclusions (see Residue below) -- forcing them
into this ticket's own scope would have meant either duplicating `frob
sys audit` (`check`) or inventing real design work (`capacity`/
`threats`) neither this ticket's plan nor its scope anticipated.

## Changed

- src/frob/_cli_parsers/_misc.py: `_add_sys_trace_parser` registers
  `frob sys trace <from> [to] [--through-barriers]`; `_add_sys_parser`
  wires it in as a fourth sub-parser alongside plan/export/doc/audit.
- src/frob/app/config.py: `sys_trace_from`/`sys_trace_to`/
  `sys_trace_through_barriers` fields on `AppConfig` (the CLI_WIRING_FILES
  implicit-scope grant covers this file for a FEATURE ticket).
- src/frob/app/sys_runner.py: `_run_trace` (loads every `.strata` file
  under the design dir via the existing `_load_audit_model`, builds a
  `FactBase`, calls `.reachable`) and `_print_trace_report` (prints one
  destination's witness path, or the whole closure with no destination);
  `run` dispatches `sys_command == "trace"` into it.
- docs/commands/sys.md: new `## frob sys trace (T-1480)` section (usage,
  `--through-barriers` semantics, public API, CLI wiring, and a Residue
  subsection naming the three cut verbs and why); updated the header
  verb count/list and removed the stale `not yet landed on main` negative-
  existence phrasing entirely (rephrased to avoid re-triggering NEGEXIST001
  rather than bind a `frob:until` to a not-yet-real draft id, since the
  draft->real renumbering-in-docs is not part of what `frob ticket land`
  rewrites -- only ticket bodies/waive sites are, per
  `_rewrite_draft_references_in_bodies`/`_rewrite_draft_references_in_
  waive_sites`).
- tests/unit/test_app_sys_trace.py (new file): `TestSysTrace`, 4 tests.
  Kept separate from `tests/unit/test_app_runners_batch7.py` (the file
  the sibling `plan`/`doc`/`export`/`audit` runner tests live in)
  deliberately -- that file's OTHER, unrelated test classes
  (`TestTicketStart`, `TestSpawnBackgroundSweep`, `TestTicketEvidence`,
  ...) have their own `frob:tests`/call-graph edges reaching well outside
  T-1480's declared scope; adding the whole file to scope produced real
  SCOPE002 closure errors for symbols this ticket never touches. A
  dedicated file keeps the scope closure honest.

## Evidence

4 pytest node ids, `frob ticket evidence T-1480` bound, all observed
passing:
- tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_witness_path_to_destination
- tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_whole_closure_with_no_destination
- tests/unit/test_app_sys_trace.py::TestSysTrace::test_unknown_source_node_exits_1
- tests/unit/test_app_sys_trace.py::TestSysTrace::test_unreachable_destination_exits_1

`uv run pytest tests/unit/test_app_sys_trace.py -q`: 4 passed.
`uv run frob check --only test --ticket T-1480`: gate:TEST 0 errors (24
pre-existing repo-wide warnings, 4 pre-existing waivers, none new).

No acceptance criteria were declared on this ticket, so evidence is not
bound via `--accepts`.

## Filed (residue, all real ids verified on main after land)

- T-1927 -> "design a population/date-projected capacity
  evaluator for frob sys capacity" (feature, scope src/frob/strata/**):
  `capacity` needs a real population/date-projected evaluator that does
  not exist anywhere in `frob.strata` yet.
- T-1925 -> "design a ThreatViolation-to-boundary join for a
  boundary-scoped frob sys threats" (feature, scope
  src/frob/strata/_threat.py): `threats [boundary]` needs a real join
  from `ThreatViolation.node` to a boundary's flow endpoints that does
  not exist anywhere yet.
- T-1926 -> "decide: drop 'frob sys check' from roadmap.md's
  CLI surface (duplicates 'frob sys audit')" (docs, scope
  docs/strata/roadmap.md): `frob sys audit` already satisfies `check`'s
  stated premise; recommend dropping `check` from the roadmap rather than
  building a duplicate, but that is a docs decision outside this
  ticket's own scope to make unilaterally.

## Disclosed cuts

- `check`/`capacity`/`threats` NOT built -- see Residue above, matching
  the prior attempt's own investigation of why each is either a
  duplicate (`check`) or needs real design work first (`capacity`/
  `threats`) rather than being CLI-glue gaps like `trace` was.
- A separate, pre-existing, cross-cutting gate limitation surfaced while
  filing the residue tickets above: `frob check --only scope --ticket
  T-1480` reports 3 SCOPE001 errors against the residue tickets' own
  `tickets/T-draft-*/ticket.md` shard files, because `frob.gates.
  __init__._TICKET_REF_RE` (`r"T-\d{4}"`) never matches a draft id's
  `T-draft-<hex>` shape in the filing commit's subject, so
  `_commit_exempts_file`'s cross-ticket exemption (T-0108) can never
  recognize a draft ticket's own scope over its own shard commit -- this
  reproduces for ANY ticket that files a residue draft, not something
  specific to T-1480's own changes. `frob check --land-parity` (the
  actual land-time evaluation, `frob.app.ticket_runner._land_cmd.
  land_parity_findings`) reports clean against the same tree (0 unscoped
  errors), confirming this is exactly the `--ticket`-scoped-run noise
  playbook section 6g documents, not a real land blocker -- left
  unfixed since `src/frob/gates/__init__.py` is outside this ticket's
  declared scope; not separately filed as a residue ticket here because
  T-1916 (already on the ledger, filed independently before this ticket
  started) already tracks a related SYS-IFACE-ORDER gate-claim gap in
  the same family of "does the enforced gate match what CHK-GATE-* docs
  claim" concerns -- flagging for whoever next touches `frob.gates.
  __init__`'s SCOPE001 implementation rather than filing a fourth
  overlapping ticket.

## Gates

`frob check --only test --ticket T-1480`: gate:TEST 0 errors.
`frob check --only doclink --only docanchor --ticket T-1480`: 0 errors
(both families clean; not shown in the scope-note repro since scope/
prework/drift were run in the same invocation with them).
`frob check --only scope --only prework --ticket T-1480`: gate:SCOPE 3
errors (see Disclosed cuts above -- draft-id regex gap, not this
ticket's own scope/files), gate:PRE clean, gate:DRIFT clean (1
pre-existing waived finding, unrelated).
`frob check --land-parity`: clean -- 0 unscoped error(s), matches what
the land sweep would see (re-run twice at the same tree hash, both
clean).

### Changed
```
 tickets/T-1480/ticket.md           | 70 +++++++++++++++++++++++++++++++++++++-
 tickets/T-1925/ticket.md | 43 +++++++++++++++++++++++
 tickets/T-1926/ticket.md | 48 ++++++++++++++++++++++++++
 tickets/T-1927/ticket.md | 45 ++++++++++++++++++++++++
 4 files changed, 205 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_witness_path_to_destination` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_whole_closure_with_no_destination` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_trace.py::TestSysTrace::test_unknown_source_node_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_trace.py::TestSysTrace::test_unreachable_destination_exits_1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 2 error(s), 872 warning(s), 699 waived
- error-findings: PRE001@tickets/T-1480, REG002@docs/design/registry/check-coverage.yaml
