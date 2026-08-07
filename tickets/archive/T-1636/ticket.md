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
evidence:
- tests/unit/test_arch.py::TestMayRaiseResolver::test_qualified_except_clause_discharges_bare_named_leak
- tests/unit/test_arch.py::TestMayRaiseResolver::test_bare_reraise_of_qualified_catch_type_is_normalized
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_relative_base_dir_level_walks_exactly_to_root_returns_none
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_relative_base_dir_outside_root_returns_none_via_value_error
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_relative_base_dir_within_root_resolves
- tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_subscript_call_target_is_not_resolved
- tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_call_names_skips_unresolvable_subscript_call
- tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
- tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present
- tests/test_ticket_land.py::TestWaiveRewrapNotDeletion::test_rewrap_only_diff_is_not_flagged_as_a_deletion
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch
- tests/test_vet.py::TestFingerprintScan::test_yaml_load_with_explicit_loader_is_not_flagged
designated_repro_test: null
threat: null
component: null
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