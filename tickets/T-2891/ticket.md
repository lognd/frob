---
id: T-2891
title: twelve *SCHEMA-family gates (plus FLAGCOV) resolve UNRESOLVED off-repo and
  render as a clean pass
state: in-progress
kind: bug
origin: human
created: '2026-08-25'
priority: high
parent: T-2384
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docblocks_schema.py
- src/frob/gates/_dup_graph_schema.py
- src/frob/gates/_flag_coverage.py
- src/frob/gates/_gates_schema.py
- src/frob/gates/_native_schema.py
- src/frob/gates/_profile_schema.py
- src/frob/gates/_refs_schema.py
- src/frob/gates/_test_runner_schema.py
- src/frob/gates/_testing_schema.py
- src/frob/gates/_toplevel_scalar_schema.py
- src/frob/gates/_arch_schema.py
- src/frob/app/check_runner.py
- src/frob/check/__init__.py
- src/frob/check/_python.py
- docs/commands/check.md
- docs/modules/gates.md
- tests/unit/test_check.py
evidence_scope:
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/check/__init__.py
  reason: 'Investigation confirms the rendering/exit-code defect lives in CheckResult.as_text

    (src/frob/check/__init__.py, the per-tool pass/FAIL icon loop) and in

    _gates_family_result (src/frob/check/_python.py, which sets the gate:X

    ToolResult''s exit_code/diagnostics that as_text reads). check_runner.py only

    calls result.as_text() -- it contains no per-tool rendering logic itself.

    Adding these two files so the fix lands where the defect actually is,

    per the ticket''s own instruction not to touch the twelve resolvers.

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/check/_python.py
  reason: 'Investigation confirms the rendering/exit-code defect lives in CheckResult.as_text

    (src/frob/check/__init__.py, the per-tool pass/FAIL icon loop) and in

    _gates_family_result (src/frob/check/_python.py, which sets the gate:X

    ToolResult''s exit_code/diagnostics that as_text reads). check_runner.py only

    calls result.as_text() -- it contains no per-tool rendering logic itself.

    Adding these two files so the fix lands where the defect actually is,

    per the ticket''s own instruction not to touch the twelve resolvers.

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/commands/check.md
  reason: 'Adding the doc files the fix touches: docs/commands/check.md documents

    CheckResult.as_text''s tool-summary rendering (scope-closure warning named

    this explicitly), and docs/modules/gates.md carries the

    #unresolved-t-1664 anchor whose counting/rendering contract this ticket

    clarifies (no exit-code change, but the rendering behavior it describes

    gains a third rendered state for all-unresolved gate results).

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/gates.md
  reason: 'Adding the doc files the fix touches: docs/commands/check.md documents

    CheckResult.as_text''s tool-summary rendering (scope-closure warning named

    this explicitly), and docs/modules/gates.md carries the

    #unresolved-t-1664 anchor whose counting/rendering contract this ticket

    clarifies (no exit-code change, but the rendering behavior it describes

    gains a third rendered state for all-unresolved gate results).

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_check.py
  reason: 'gate:SCOPE SCOPE001 flagged tests/unit/test_check.py as outside declared

    scope -- it holds the new repro test (TestUnresolvedOnlyGateRendering)

    this bug ticket''s BUG002 evidence requires. Adding it to scope (it was

    only in evidence_scope, not scope, which SCOPE001 does not accept as a

    write-lease-covering entry).

    '
  actor: logan
  at: '2026-08-25'
evidence:
- tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_must_now_fire_unresolved_only_gate_is_not_rendered_as_pass
- tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_control_a_real_clean_gate_still_renders_pass
- tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_control_a_real_failing_gate_still_renders_fail
- tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_control_non_gate_info_diagnostics_are_not_caught
- tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_mixed_unresolved_and_findings_still_renders_pass_or_fail
designated_repro_test: tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_must_now_fire_unresolved_only_gate_is_not_rendered_as_pass
threat: null
component: portability
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED (coordinator, 2026-08-25): a real off-repo run of this source tree's 'frob check' against /home/logan/projects/lograder (src-layout, package 'lograder', not frob) -- saved at /tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/port-lograder.txt -- found 12 gates reporting '0 errors, 0 warnings, 1 unresolved, 0 waived' there: ARCHSCHEMA, DOCBLOCKSSCHEMA, DUPSCHEMA, FLAGCOV, GATESSCHEMA, GRAPHSCHEMA, NATIVESCHEMA, PROFILESCHEMA, REFSCHEMA, TESTINGSCHEMA, TESTRUNNERSCHEMA, TOPSCALARSCHEMA. In frob's own repo every one of these reports 0 unresolved. The other portability findings from the same run (REF 85, SELFAUDIT 98, SYS 50, OPAQUE 53, DOC 121) are real, correctly-firing off-repo findings and confirm the T-2384 retargeting already landed is working -- this ticket is scoped to the 12-gate UNRESOLVED-as-pass gap only.

ROOT CAUSE (this ticket's own investigation, corrects the coordinator's initial hypothesis): NOT a hardcoded frob-repo-relative path. Each of these 12 gates resolves an opt-in [gatename_schema] known_keys (or equivalent) dotted 'module:attribute' declaration out of the TARGET project's own frob.toml (see _docblocks_schema.py::_resolve_known_keys, and the identical shape repeated in _dup_graph_schema.py, _gates_schema.py, _native_schema.py, _profile_schema.py, _refs_schema.py, _test_runner_schema.py, _testing_schema.py, _toplevel_scalar_schema.py, _arch_schema.py, _flag_coverage.py -- all read root/frob.toml then doc.get(<table>, {}).get('known_keys') then frob.gates._docblocks_shared.resolve_dotted_symbol, a generic importlib.import_module/getattr pair with no frob-specific hardcoding). lograder DOES have its own frob.toml (verified: /home/logan/projects/lograder/frob.toml exists) -- it simply does not declare these 12 gates' opt-in schema tables, so _resolve_known_keys correctly returns Severity.UNRESOLVED with a message naming exactly which key is missing. That part is working as designed (T-1664's fail-loudly-not-silently-pass doctrine for UNRESOLVED).

THE ACTUAL DEFECT is one level up, in how an ALL-UNRESOLVED gate result is rendered/scored: Severity's own docstring (src/frob/gates/_models.py, class Severity) states outright that UNRESOLVED 'does not fail check's exit code' -- by explicit design, same as WARN. That is correct for a gate with a MIX of unresolved-and-clean findings inside an otherwise-measured project, but for the 12 gates here the ENTIRE tool result is unresolved (1 unresolved, 0 of everything else) because the gate never ran a real check at all -- and nothing in frob check's printed tool-summary/exit-code path distinguishes 'ran clean' from 'never configured, never ran' at the coarse pass/fail level a consumer skims. This is the [[catalogued-is-not-enforced]]/T-2391 silent-zero failure mode wearing the UNRESOLVED costume specifically: a newly-onboarded frob-enabled project (lograder is a real, live example, not a hypothetical) gets 12 green-looking gate lines it never configured and never ran, with no loud signal telling the operator these 12 opt-in schemas exist and are unconfigured.

INVESTIGATION NOTE for the acceptance-criteria author (already done here, recorded so it is not re-derived): do not 'fix' this by making the resolvers derive a default known_keys without a declared frob.toml entry -- these are genuinely per-project schema declarations (lograder's docblocks/gates/schema shapes are lograder's own to declare, not something frob can infer). The fix belongs in the SUMMARY/EXIT-CODE path: an all-UNRESOLVED tool result must be visibly distinguished from an all-clean one, not just carry an accurate count buried in one summary line.

ACCEPTANCE:
(a) Given a frob check run where a gate's entire ToolResult contains only UNRESOLVED diagnostics (zero ERROR, zero WARN), when the run's tool summary and exit-code/pass-fail determination are produced, then that gate is never presented in a form indistinguishable from a clean pass -- proven by a must-now-fire fixture: a non-frob-named src-layout project with a valid frob.toml that deliberately omits ONE of these 12 gates' known_keys declarations, asserting the rendered tool-summary output (or --json ToolResult) marks that gate's row as attention-needed/unresolved-only rather than folding it into a passing count, paired with a must-still-pass control: this repo's own frob check, which declares all 12 known_keys and must continue reporting 0 unresolved for each, unchanged.
(b) Given the same fixture project but WITH all 12 known_keys correctly declared (pointing at real dotted module:attribute targets defined in the fixture project's own tree, not frob's), when each of the 12 gates runs, then each resolves its schema source from the fixture project's own declared frob.toml/source tree and reports a real result (error, warning, or a genuine empty clean pass) instead of UNRESOLVED -- proving the existing resolve_dotted_symbol path is already portable once configured, isolating this ticket to the summary/exit-code gap in (a) rather than requiring changes to the resolvers themselves.