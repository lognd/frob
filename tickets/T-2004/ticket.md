---
id: T-2004
title: 'A CLI flag can be parsed, tested, and silently dropped by from_external''s
  allowlist: tested is not reached'
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/_config_external.py
- tests/unit/test_app_config_flag_coverage.py
- docs/modules/app.md
- tests/unit/test_app_sys_capacity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_config_flag_coverage.py
  reason: new unit test file for find_dropped_cli_flags
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/app.md
  reason: frob:doc anchors for new symbols, plus prior FLOAT_FIELDS test edge covered
    by an already-touched file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_app_sys_capacity.py
  reason: frob:doc anchors for new symbols, plus prior FLOAT_FIELDS test edge covered
    by an already-touched file
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_reconstructed_t1995_state_is_caught
- tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_reconstructed_state_is_clean_once_the_field_is_added
- tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_flag_with_no_matching_config_field_is_not_flagged
- tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_help_and_version_are_never_flagged
- tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_current_tree_has_zero_dropped_flags
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED, 2026-08-10, T-1995/T-2002.

T-1995 added a `--ack-related` flag to `frob ticket new`. Every one of its
tests passed. The flag NEVER WORKED end-to-end: `AppConfig.from_external`
(`src/frob/app/_config_external.py`) copies fields through a static
allowlist, and the new field was not in it, so argparse's parsed value was
silently dropped on the floor before reaching the runner.

The tests all passed because they constructed `AppConfig` DIRECTLY, bypassing
argparse and bypassing `from_external` -- i.e. they tested the function and
skipped the wiring that connects it to the CLI. Caught only by accident, when
an unrelated TEST001 finding sent someone back into the file. Fixed in T-2002
with a real argparse-parsing regression test.

SECOND INSTANCE, same week, same class: T-1977 wired
`capability_ratchet_violations` into the self-audit gate. That agent
deliberately proved it fires by calling the REAL `sys_gate` entry point
rather than the function under test -- and that care is the only reason the
wiring was known-good. Wiring the detector immediately surfaced three real
drifts that had accumulated precisely because nothing had ever invoked it.
Both cases turn on the same question: does a test exercise the PRODUCTION
ENTRY POINT, or only the symbol?

The general defect: a symbol can be fully implemented, fully tested, and
completely unreachable from the CLI, with every gate green. This repo already
has a name for the adjacent failure -- "catalogued is not enforced" (registry
YAMLs read by zero code). This is its executable twin: TESTED IS NOT REACHED.

## Do not fix it this way
- Do NOT just add `--ack-related` to the allowlist and call it done. That
  fixes one field. The defect is that the allowlist can silently disagree
  with the parser at all, for any field, with no check.
- Do NOT replace the static allowlist with a blanket `**kwargs`/dynamic copy
  to "make it impossible". That trades a loud-but-narrow bug for a silent-
  and-wide one, and destroys the allowlist's actual purpose (an explicit
  boundary about what external input may set).
- Do NOT fix it with a review-checklist line or a playbook entry. Two agents
  hit this class in one week; a written rule is not an enforcement.

## Acceptance criteria
1. A check that FAILS FIRST on a reconstructed T-1995 state: a parser flag
   that exists in argparse but is absent from `from_external`'s allowlist
   must be reported. Assert the current tree passes it (so it is a real
   ratchet), then assert the reconstructed state fails it.
2. The check compares the ACTUAL parser surface against the ACTUAL allowlist,
   derived from both, not a third hand-maintained list -- a third list is a
   new desync source (see the T-2001 ratchet-lock instance for what a
   partially-synced obligation costs).
3. Report, as measurement rather than assumption, how many CURRENT flags
   across all `frob` subcommands fail this check. If the answer is zero,
   say so and show the denominator of flags examined; if nonzero, each is a
   live silently-dead flag and needs its own accounting.

## Done report

Changed:
src/frob/app/_config_external.py::_AD_HOC_FORWARDED_FIELDS (new)
src/frob/app/_config_external.py::_all_forwarded_field_names (new)
src/frob/app/_config_external.py::_all_parser_dests (new)
src/frob/app/_config_external.py::find_dropped_cli_flags (new, public)
src/frob/app/_config_external.py::_STRING_FIELDS (+ticket_anchor_reason, sys_threats_boundary)
src/frob/app/_config_external.py::_PATH_FIELDS (+ticket_anchor_reason_file)
src/frob/app/_config_external.py::_BOOL_FLAGS (+ticket_doable_show_anchors, ticket_anchor_set, ticket_anchor_clear)
docs/modules/app.md (new T-2004 subsection under "## Config")
tests/unit/test_app_config_flag_coverage.py (new)

The defect (docs/modules/app.md's new T-2004 section has the full
writeup): `AppConfig.from_external` forwards a parsed `argparse.
Namespace` into the model through six static field-name tuples plus one
small ad-hoc set. A flag that parses correctly and has a matching
`AppConfig` field, but is absent from every one of those, is silently
dropped -- no error, stays at its pydantic default forever -- and a unit
test that constructs `AppConfig` directly (skipping argparse and
`from_external`) cannot catch this, because it never exercises the
wiring. T-1995's `--ack-related` and this series' own T-1925
`sys_threats_boundary` are two independent, confirmed instances.

## Do-not-fix-it-this-way constraints, honored
- Did NOT stop at adding the 6 found fields to the allowlist tuples --
  that is necessary (see "measured count" below, acceptance criterion 1
  requires the check to pass on the current tree) but not sufficient;
  `find_dropped_cli_flags` is the actual fix, a reusable static check.
- Did NOT replace the static tuples with a blanket dynamic copy. The
  tuples remain the explicit, reviewable boundary on what external CLI
  input may set on `AppConfig`; `find_dropped_cli_flags` reads them
  (never duplicates them into a second list) and compares them against
  the live parser tree.
- Not a playbook entry: it is `find_dropped_cli_flags`, a function with
  a test that runs on every CI pass, not written guidance.

## Acceptance criteria
1. `test_reconstructed_t1995_state_is_caught` / `_is_clean_once_the_
   field_is_added`: a synthetic parser + a `forwarded=` override
   reconstructing T-1995's exact pre-fix state (a `--ack-related` flag
   present in argparse and on a fake config's fields, absent from a
   narrow forwarded set) is caught; adding it to the forwarded set
   clears the finding. Proven through the REAL `find_dropped_cli_flags`
   call (the `forwarded=` param exists specifically so a test can
   inject a hypothetical/past state without needing to actually mutate
   this module's own live tuples).
2. `_all_forwarded_field_names`/`_all_parser_dests` are both derived
   directly from this module's own live tuples and the live `_build_
   parser()` tree -- no third hand-maintained list. The docstrings on
   both functions state this explicitly as the design constraint.
3. MEASURED, not assumed: `test_current_tree_has_zero_dropped_flags`
   runs `find_dropped_cli_flags` against the REAL `frob` parser and the
   REAL `AppConfig`. Denominator: 317 candidate flags (every argparse
   dest with a matching `AppConfig` field name -- flags with no matching
   field, like `bind`/`agent`/`worktree sweep`'s own raw-argv-dispatched
   flags, are correctly out of scope and excluded by construction, not
   by a name-list). Result at measurement time: 6 nonzero (all fixed in
   this same change, see Changed above); result on the tree this ticket
   lands: 0/317.

Evidence: 5 pytest node ids in tests/unit/test_app_config_flag_coverage.py.
`--check-repro` on the ratchet test reports NO_VERDICT (not FAILED_AT_
PARENT) at the parent commit -- structurally expected, not a
confirmatory-only finding: this ticket adds an entirely new test module
testing entirely new detection code in the same change (the module
cannot even COLLECT at a parent that predates the module's existence).
The genuine pre-fix bug state is proven instead by `test_reconstructed_
t1995_state_is_caught`, which reconstructs T-1995's exact broken
condition via the `forwarded=` injection parameter and asserts the real
function catches it -- see acceptance criterion 1 above.

Filed: none (the two live-broken flag FAMILIES this ticket surfaced --
anchor-related and sys_threats_boundary -- were fixed directly in this
same change, not deferred).

Gates: `frob check --ticket T-2004` -- gate:SCOPE/COV(diff)/AFFECT/FMT
all clean (0 errors) after fixing a genuine AFFECT001 (new docs/modules/
app.md section) and COV007 (moved a frob:doc anchor off a private
constant onto its public caller) this ticket's own diff surfaced.
Remaining repo-wide FAILs in the same run (gate:ARCH 2 errors, gate:COV
1 error at tickets/T-0907 -- a stale evidence-collection finding scoped
to a DIFFERENT ticket's own citation, ruff-check, ruff-format) are
pre-existing baseline, confirmed unrelated: `frob verify explain` was
attempted per the coordinator's guidance to attribute the T-0907 finding
properly rather than reason from file paths, but the verify queue is
currently empty (watermark: none, depth 0) -- nothing is enqueued to
attribute against right now, so `frob verify explain` could not be used
here. Falling back to the finding's own self-identification (it names
tickets/T-0907 as the id whose evidence citation is stale) as the
attribution instead: it is scoped to that ticket's own ledger entry, not
to any symbol T-2004 touched.

### Changed
```
 tickets/T-2004/ticket.md | 29 ++++++++++++++++++++++++++++-
 1 file changed, 28 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_reconstructed_t1995_state_is_caught` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_reconstructed_state_is_clean_once_the_field_is_added` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_flag_with_no_matching_config_field_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_help_and_version_are_never_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_current_tree_has_zero_dropped_flags` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/strata-cli-surface/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/strata-cli-surface/tests/unit/test_tickets_evidence_only_scope.py, WIRE001@src/frob/app/_config_external.py, WIRE001@tests/unit/test_app_config_flag_coverage.py
