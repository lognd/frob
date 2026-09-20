---
id: T-1636
title: Fix gate:EXHAUST qualified-except-clause matching bug in mayraise resolver,
  drain EXHAUST+COV warnings
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_mayraise.py
- src/frob/gates/**
- src/frob/app/**
- src/frob/refactor/**
- src/frob/strata/**
- src/frob/tickets/**
- src/frob/release/__init__.py
- src/frob/doctor.py
- src/frob/lang/__init__.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense COMPLIANCE005 vacuity-closure narrative into T-1244 body
  actor: logan
  at: '2026-09-19'
  old_length: 3381
  new_length: 5073
- mode: append
  reason: condense SYS107 threshold rationale into T-1636 body
  actor: logan
  at: '2026-09-19'
  old_length: 5073
  new_length: 6269
evidence:
- tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_qualified_except_clause_discharges_bare_named_leak
- tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_bare_reraise_of_qualified_catch_type_is_normalized
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_relative_base_dir_level_walks_exactly_to_root_returns_none
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_relative_base_dir_outside_root_returns_none_via_value_error
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_relative_base_dir_within_root_resolves
- tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_subscript_call_target_is_not_resolved
- tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_call_names_skips_unresolvable_subscript_call
- tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
- tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present
- tests/ticket_land_suite/test_waive_deletion.py::TestWaiveRewrapNotDeletion::test_rewrap_only_diff_is_not_flagged_as_a_deletion
- tests/ticket_land_suite/test_archive.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_yaml_load_with_explicit_loader_is_not_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Two untracked findings families surfaced by an unscoped `frob check`:
gate:EXHAUST (33 unwaived warnings) and gate:COV (33 unwaived warnings,
overwhelmingly COV007). This ticket covers gate:EXHAUST triage:

- EXHAUST003 (21 unwaived): every sampled finding traces to the same
  established resolution-coverage-gap class T-1402/T-1062/T-1371 already
  waived 118 times for -- a leaked UNKNOWN attributable to an unresolved
  callee (stdlib helper, cross-module private helper, compiled regex
  search, etc), never a real unhandled error. Fix: per-function
  `frob:waive EXHAUST003` following the established reason convention.

- EXHAUST002 (12 unwaived): sampling showed 11 of 12 are also resolver
  over-approximation, but of TWO distinct mechanical causes newly
  root-caused here:
  (a) `_SUBSCRIPT_RAISE = "KeyError"` in `frob.arch._mayraise` fires for
      ANY `x[y]` syntax anywhere in a function's body or its resolved
      callees, with no distinction for a `dict.get`-guarded/safe/tuple
      subscript -- the same false-positive shape already disclosed in
      existing EXHAUST002 waivers.
  (b) a genuine ROOT-CAUSE BUG: `frob.arch._python._py_except_exception_type`
      captures a QUALIFIED except-clause type's dotted text verbatim
      (`except json.JSONDecodeError:` -> caught text "json.JSONDecodeError"),
      while `_mayraise._STDLIB_QUALIFIED_RAISERS` (e.g. `"json.loads":
      frozenset({"JSONDecodeError"})`) attributes the BARE name. `_catches`/
      `_is_subtype` then compares "JSONDecodeError" against
      "json.JSONDecodeError" and never matches -- so a function that
      genuinely, correctly catches `except json.JSONDecodeError:` (or a
      tuple catch whose first member is dotted) never discharges the leak,
      and EXHAUST002 fires a false positive on code that already handles
      the exception correctly. Confirmed at
      src/frob/gates/_fix_engine.py::_e501_lines_for_file and
      src/frob/tickets/_land.py::_read_land_lock_holder (both catch
      `json.JSONDecodeError` explicitly and still show the leak).
      Fix at the RULE level: normalize both operands of the type-text
      comparison to their bare (rightmost dotted-component) name before
      comparing, in `frob.arch._mayraise` -- not a per-site waiver, since
      site-level waivers would hide a real matching bug from every other
      qualified-except-clause site in the repo, present or future.
  1 of 12 (src/frob/gates/_fmt_directives.py::_write_formatted) is a
  genuine INTENTIONAL propagation (catches OSError, logs+cleans up
  tempfile, re-raises) -- fixed with a `# frob:raises OSError` directive,
  not waived.

Acceptance:
- The `_catches`/qualified-name matching bug is fixed in
  `frob.arch._mayraise` with a regression test proving a dotted except
  clause discharges a bare-named leak.
- `_write_formatted` carries `# frob:raises OSError`.
- Every remaining unwaived EXHAUST002/EXHAUST003 finding (after the rule
  fix reduces the count) carries a specific, non-generic
  `frob:waive` reason naming the actual unresolved callee/subscript,
  matching the established T-1402/T-1062/T-1371 reason convention -- never
  a copy-pasted blanket reason.
- `frob check --only exhaustive_handling` unscoped shows 0 unwaived
  warnings for gate:EXHAUST (or the exact honest remainder is disclosed
  in the Done report with reasoning, not silently left).

<!-- narrative-moved:src/frob/strata/_compliance.py:1043:T-1636 -->
frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#compliance005compliance007-compliance-registry-vs-model-checking-t-1244  # noqa: E501
frob:waive COV007 reason="T-1636: the anchored EXHAUSTIVENESS-GATE.md section is a \
deliberate design doc walking through this exact private mapping's own \
vacuity-closure rationale (T-1244), immediately below in this same module's own \
multi-paragraph docstring -- same T-0524/T-0529 per-symbol architecture-doc \
precedent every other COV007 waiver in this repo already carries, not accidental \
drift onto a private symbol"
: T-1244 (gate-vacuity closure): `_check_cmpl_registry_unit_dispositions`
: (COMPLIANCE005) only proves a `CMPL_REGISTRY_UNIT_IDS` member carries
: SOME `handled_by`/`out_of_scope` string -- for 16 of the 17 units that
: string is the SELF-referential `handled_by:COMPLIANCE005`, which is
: circular: "this framework is handled by the check that verifies a
: disposition string exists" proves nothing about whether any real
: `RegulationEntry`/mitigation/attestation backs THAT framework's actual
: obligations. `CMPL-FROB-CATALOG-ENTRIES` is the one legitimate
: exception -- it is a meta-row COUNTING `COMPLIANCE_CATALOG`'s own real
: entries, so its self-reference is not vacuous (T-1250 confirms this
: explicitly rather than let it ride the same generic shape as the other
: 16). Maps each vacuously-self-referential unit to the per-framework
: triage ticket (T-1245-T-1249) that owns its real (a)/(b)/(c)/(d)
: classification -- named here, not re-derived, so `_cmpl_unit_backing_
: violation`'s message always points at live, open follow-up work.

<!-- narrative-moved:src/frob/strata/_selfconform_ids.py:213:T-1636 -->
frob:doc docs/strata/surface.md#may-scope
frob:waive COV007 reason="T-1636: docs/strata/surface.md's may-scope section \
(T-1440/T-1451) documents the SYS107 via-less-large-node advisory this constant \
configures -- same T-0524/T-0529 per-symbol architecture-doc precedent every other \
COV007 waiver in this repo already carries, not accidental drift onto a private \
symbol"
: SYS107's default "large node" file-count threshold (T-1451) --
: deliberately a round, generous number (LARGE001's own file-SIZE
: threshold precedent, `frob.arch._check_large_file`, is the closest
: existing analog in this repo for "a size past which a flat/unscoped
: declaration stops being informative") rather than a data-derived one;
: `[strata] require_may_scope_threshold` in `frob.toml` overrides it per
: repo (`_scope_config.py::StrataScopeConfig`).
frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
rule family -- this symbol only moved to a sibling module verbatim (same name, same \
body/signature), no behavior change, so the affects()-closure doc it names needs no \
update"
frob:ticket T-2729