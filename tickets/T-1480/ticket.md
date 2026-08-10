---
id: T-1480
title: build frob sys check/trace/capacity/threats verbs
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/sys_runner.py
- docs/commands/sys.md
- src/frob/strata/_mutation_audit.py
- src/frob/_cli_parsers/_misc.py
- tests/unit/test_app_sys_trace.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: trace verb needs its argparse registration point; individual _cli_parsers
    modules are not covered by the FEATURE CLI_WIRING_FILES grant per T-1848, structurally
    required for a dispatch-reachable subcommand
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: T-1480's own new trace tests live here, matching the existing TestSysAudit/TestSysRunnerDispatch
    precedent in the same file
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/test_app_sys_trace.py
  reason: dedicated new test file for T-1480's trace tests, kept out of the shared
    batch7 file to avoid its unrelated-class SCOPE002 closure noise
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: tests/unit/test_app_runners_batch7.py
  reason: trace tests moved to a dedicated file (tests/unit/test_app_sys_trace.py);
    this shared file's own unrelated test classes pull in SCOPE002 closure errors
    this ticket has no business touching
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'WIRE001: new sys_trace_from/sys_trace_to/sys_trace_through_barriers argparse
    dest fields must be copied into this file''s field-name tuples or AppConfig.from_external
    silently drops them (T-1422 shape)'
  actor: logan
  at: '2026-08-09'
evidence:
- tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_witness_path_to_destination
- tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_whole_closure_with_no_destination
- tests/unit/test_app_sys_trace.py::TestSysTrace::test_unknown_source_node_exits_1
- tests/unit/test_app_sys_trace.py::TestSysTrace::test_unreachable_destination_exits_1
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_app_runners_batch7.py::TestSysTrace::test_trace_prints_witness_path_to_destination
  new_node: tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_witness_path_to_destination
  reason: moved trace tests to a dedicated file to avoid batch7's unrelated-class
    SCOPE002 closure noise
  actor: logan
  at: '2026-08-09'
- old_node: tests/unit/test_app_runners_batch7.py::TestSysTrace::test_trace_prints_whole_closure_with_no_destination
  new_node: tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_whole_closure_with_no_destination
  reason: moved trace tests to a dedicated file to avoid batch7's unrelated-class
    SCOPE002 closure noise
  actor: logan
  at: '2026-08-09'
- old_node: tests/unit/test_app_runners_batch7.py::TestSysTrace::test_unknown_source_node_exits_1
  new_node: tests/unit/test_app_sys_trace.py::TestSysTrace::test_unknown_source_node_exits_1
  reason: moved trace tests to a dedicated file to avoid batch7's unrelated-class
    SCOPE002 closure noise
  actor: logan
  at: '2026-08-09'
- old_node: tests/unit/test_app_runners_batch7.py::TestSysTrace::test_unreachable_destination_exits_1
  new_node: tests/unit/test_app_sys_trace.py::TestSysTrace::test_unreachable_destination_exits_1
  reason: moved trace tests to a dedicated file to avoid batch7's unrelated-class
    SCOPE002 closure noise
  actor: logan
  at: '2026-08-09'
threat: null
component: null
anchor: false
anchor_reason: null
---
docs/commands/sys.md documents frob sys as having five verbs today
(plan/doc/export/audit/sync-interface) and names check/trace/capacity/
threats as later phase-5 verbs not yet landed on main. No ticket
currently tracks building these four verbs. Found while draining
NEGEXIST001 (T-1477): the doc's absence-claim had no
frob:until binding.

## Failure log
- 2026-08-08 attempt 1: Undoable as scoped: adding any of check/trace/capacity/threats as a real,
CLI-dispatchable 'frob sys' verb requires registering a new argparse
subparser in src/frob/_cli_parsers/_misc.py (_add_sys_doc_and_audit_parsers's
sibling registration point, called from both its own top-level 'frob sys'
group at _misc.py:~580 and from _design.py:~57's 'frob design sys'
regrouping mirror) -- both files are explicitly out of scope for this
dispatch (owned by another agent: "Do NOT touch ... src/frob/_cli_parsers/**").

T-1480's declared scope (src/frob/app/sys_runner.py, docs/commands/sys.md,
src/frob/strata/_mutation_audit.py) has no path to a dispatch-reachable
verb without them -- a verb registered only in sys_runner.py's run()
dispatch function with no CLI parser entry can never actually be invoked
(cfg.sys_command would never be set to it by argparse), which is exactly
the "tested components wired into nothing" failure mode this dispatch's
own instructions warn against.

Also found: src/frob/strata/_mutation_audit.py (in this ticket's declared
scope) is unrelated to this ticket's actual work -- it is T-1203/T-1328's
may-capability mutation-audit harness (proves every 'may' declaration is
load-bearing and double-detected), not a sys_runner CLI concern. Same
apparent mis-scoping pattern already found and corrected on T-1482 earlier
in this series (that ticket's declared scope named _mutation_audit.py and
_native_staleness.py, also both unrelated to its actual policy-refinement
work).

Investigated what each of the four verbs would need before concluding
this, per the "check whether the premise is still true" instruction:

- 'check' ("parse + elaborate + prove + report", roadmap.md): this
  premise looks ALREADY SATISFIED by the existing 'frob sys audit'
  (sys_runner.py::_run_audit) -- it parses, elaborates, runs the full
  exhaustiveness/self-conformance/resource-contention/mode-conformance/
  reliability conjunction, and reports pass/fail with named gaps. Adding
  a second, narrower 'check' verb duplicating this would cut against the
  standing "prefer deleting a verb over adding one" directive, not serve
  it -- likely a real one for the CLI-parser-owning agent to drop from
  the roadmap doc rather than build, once that scope opens up.
- 'trace <from> <to>': genuinely new and cheaply buildable --
  'frob.strata._facts.FactBase.reachable(src)' already returns the exact
  witness-path closure this verb would print; only the CLI parser +
  runner glue is missing.
- 'threats [boundary]': 'frob.strata._threat.evaluate_threats' already
  computes the full THREAT001-003 violation set; a boundary-scoped
  filter needs a real join from 'ThreatViolation.node' to the boundary's
  flow endpoints that does not exist anywhere yet -- more design work
  than a CLI wrapper.
- 'capacity [--population N | --at DATE]': no existing evaluator
  projects capacity thresholds against a POPULATION or DATE parameter at
  all ('_starvation.py''s capacity checks are static, not projected) --
  this is new modeling work, not a CLI-glue gap.

Recommendation for whoever next holds src/frob/_cli_parsers/**: 'trace'
is the cheapest real win once the parser files are available; 'check' is
probably better resolved by deleting it from the roadmap doc than by
building a duplicate of 'audit'; 'threats'/'capacity' need real design
work before a CLI verb is meaningful.

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
