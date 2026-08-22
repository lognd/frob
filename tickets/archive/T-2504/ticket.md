---
id: T-2504
title: 'confined to: prove path confinement on the existing summary engine, report-only
  first'
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: high
parent: T-2501
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/summary.py
- docs/modules/graph.md
- tests/unit/test_confinement_lattice.py
- tickets/T-2504/census-2026-08-18-raw.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/graph.md
  reason: 'T-2504: doc anchors + regression tests + committed census result for the
    confinement lattice deliverable'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_confinement_lattice.py
  reason: 'T-2504: doc anchors + regression tests + committed census result for the
    confinement lattice deliverable'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tickets/T-2504/census-2026-08-18-raw.json
  reason: 'T-2504: doc anchors + regression tests + committed census result for the
    confinement lattice deliverable'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_confinement_lattice.py::TestConfinementLatticePositiveControl::test_absolute_literal_write_is_escaped
- tests/unit/test_confinement_lattice.py::TestConfinementLatticePositiveControl::test_ordinary_tmp_path_write_is_rooted_not_escaped
- tests/unit/test_confinement_lattice.py::TestConfinementLatticeUnknown::test_unresolved_private_helper_call_poisons_to_unknown
- tests/unit/test_confinement_lattice.py::TestConfinementLatticeUnknown::test_env_lookup_feeding_a_write_is_escaped_not_unknown
- tests/unit/test_confinement_lattice.py::TestConfinementLatticeHelperPropagation::test_helper_return_value_confinement_propagates_to_caller_site
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 5f01c7b01120786a08316d1bd004533eb8f5ddf2
---
User directive 2026-08-18: `confined to` must be STATICALLY PROVABLE. A
declaration nobody can check is a comment with syntax.

DO NOT BUILD A NEW ANALYSIS. `frob.graph.summary` is already a
per-function bottom-up fixpoint over the call graph with an explicit
lattice and an SCC-ordered worklist, and its own docstring records the
T-0745 design constraint: "one engine, not two -- a future consumer
should host its own lattice over the exact same SCC-ordered worklist
instead of re-deriving call-graph traversal." Confinement provenance IS
that consumer. Host a lattice; do not write a second traversal.

The engine already enforces the honesty this needs (T-0745 NO-FAIL-SILENT
mandate): an unresolved callee POISONS the caller's summary and every
transitive caller, poisoning never resets, and functions outside the
reachable set are reported in `not_analyzed` rather than given a silently
empty summary.

LATTICE:

    ROOTED(r)   derives from a sanctioned root
    ESCAPED     provably outside: absolute literal, Path.home(),
                os.getcwd(), os.environ[...], the repo root
    UNKNOWN     unprovable; poisons and propagates

Sanctioned roots are DECLARED, not hardcoded: tmp_path /
tmp_path_factory, tempfile.*, plus any project-declared fixture the
engine has itself proven confinement-preserving.

Confinement-preserving ops (proof survives): `/` join with a relative
literal, os.path.join with relative components, .with_name/.with_suffix.
Escaping ops (proof dies): absolute literals, `..`, abspath/realpath of
an unknown, home(), getcwd(), env lookups.

Helpers get summaries like anything else: `def _write_fixture(tmp: Path)`
summarizes as "param0 confined => result confined", computed bottom-up on
the existing worklist. That is what makes ~350 sites tractable without
annotating each one.

WHY THIS COMPOUNDS WITH THE CONFIG LINT (the user's point): the only way
to be PROVABLY confined is to derive from a declared source, so
`Path("/tmp/foo")` is ESCAPED -- correctly, and for reasons beyond
confinement: it breaks on Windows and it collides under parallel jobs.
This very session writes to $CLAUDE_JOB_DIR/tmp precisely because
parallel background jobs clobber each other in /tmp. The confinement
proof rejects the hardcoded path for the same underlying reason the
config lint would. These are ONE rule with two value classes, not two
rules that agree. Build the engine once with the value class as a
parameter.

STAGING -- split the finding by verdict, do not ship one gate:
  ESCAPED -> ERROR from birth. Few, each a real bug. A test writing the
             repo root is in this class, and root pollution deadlocked
             four agents on 2026-08-18.
  UNKNOWN -> WARN with a ratchet. Burn down by making code provable or
             waive with a reason.

FIRST DELIVERABLE IS REPORT-ONLY. Run the lattice and publish a measured
PROVEN / ESCAPED / UNKNOWN census across the ~352 fs.write sites BEFORE
any severity is assigned. Poisoning propagates, so ONE unresolved callee
inside a common test helper can poison hundreds of sites and produce a
wall of UNKNOWN. That is correct behaviour and it could still make the
gate unusable on day one. Learn it from a measurement, not from a
fleet-wide red floor.

POSITIVE CONTROL, BOTH DIRECTIONS, MANDATORY: a planted escaping write
must FIRE; the ordinary tmp_path pattern must NOT.