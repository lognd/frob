---
id: T-0528
title: 'COV006 checker-blindness calibration: 56 residual findings across 4 classes'
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/gates.md
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov006_flags_test_with_no_call_graph_reachability
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_calls_the_bound_symbol
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_reaches_via_same_file_public_wrapper
- tests/test_gates.py::TestCoverageGate::test_cov006_still_fires_when_no_public_wrapper_reaches_the_target
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_reaches_via_two_hop_wrapper_chain
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_wrapper_called_via_import_alias
- tests/test_gates.py::TestCoverageGate::test_cov006_never_fires_for_a_public_target
designated_repro_test: null
threat: null
component: null
---
T-0523 triaged the ~59 out-of-scope COV006 findings measured after T-0516.
3 were genuinely wrong/stale bindings and were fixed directly (see T-0523's
Done report). The remaining 56 all fall into four checker-blindness classes
that `_cov006`/`_cov006_public_wrapper_reachable` (frob.gates.__init__)
structurally cannot see, none of which T-0516's two-hop same-file rescue
addresses. Filed as ONE calibration ticket (not four) since all four share
one root fix direction: the checker only ever looks at a 2-file scope
(`(test_file, target_file)`) and does a same-file-only public-wrapper
rescue -- every class below is a variant of "the real reachability proof
needs information `_cov006` never gathers."

**Class 1 -- framework/language-implicit dispatch (14 findings).** The
private target is invoked by the Python runtime or a decorator-driven
framework (pydantic `@field_validator`, module `__getattr__`, a context
manager's `__exit__`), never by a literal `name(...)` call anywhere in
source -- `_called_names`'s token scan (frob.graph.callgraph) can only ever
see `identifier` immediately followed by `(`, which by construction cannot
represent implicit protocol dispatch:
- `tests/test_serve.py::TestServeGetattr.test_getattr_resolves_lazy_server_names -> src/frob/serve/__init__.py::__getattr__`
- `tests/test_serve.py::TestServeGetattr.test_getattr_unknown_name_raises_attribute_error -> src/frob/serve/__init__.py::__getattr__`
- `tests/unit/test_render.py::TestProgress.test_progress_context_manager_clears_on_exit -> src/frob/render/_renderer.py::Progress.__exit__`
- `tests/unit/test_render.py::TestProgress.test_progress_context_manager_clears_even_on_exception -> src/frob/render/_renderer.py::Progress.__exit__`
- `tests/test_tickets.py::TestScopeMatching.test_comma_joined_entry_splits -> src/frob/tickets/_models.py::_split_scope_entries` (invoked via `Ticket`'s pydantic `@field_validator` `_normalize_scope`, itself never called by name in the test)
- `tests/unit/strata/test_host.py::TestHostOwnsModeValidation.test_valid_octal_mode_accepted -> src/frob/strata/_host.py::HostOwns._validate_mode`
- `tests/unit/strata/test_host.py::TestHostOwnsModeValidation.test_setuid_four_digit_mode_accepted -> src/frob/strata/_host.py::HostOwns._validate_mode`
- `tests/unit/strata/test_host.py::TestHostOwnsModeValidation.test_non_octal_mode_rejected -> src/frob/strata/_host.py::HostOwns._validate_mode`
- `tests/unit/strata/test_host.py::TestHostOwnsModeValidation.test_out_of_range_digit_mode_rejected -> src/frob/strata/_host.py::HostOwns._validate_mode`
- `tests/unit/strata/test_host.py::TestHostManifestListensValidation.test_valid_port_accepted -> src/frob/strata/_host.py::HostManifest._validate_listens`
- `tests/unit/strata/test_host.py::TestHostManifestListensValidation.test_out_of_range_port_rejected -> src/frob/strata/_host.py::HostManifest._validate_listens`
- `tests/unit/strata/test_host.py::TestHostManifestListensValidation.test_zero_port_rejected -> src/frob/strata/_host.py::HostManifest._validate_listens`
- `tests/unit/strata/test_krb.py::TestKrbValidation.test_spn_without_runs_as_is_malformed -> src/frob/strata/_elaborate.py::_validate_krb` (invoked via a tuple-of-validators dispatched by a loop variable in `_run_elaborate_validators`, not by its own name)
- `tests/unit/strata/test_krb.py::TestKrbValidation.test_spn_with_runs_as_elaborates_cleanly -> src/frob/strata/_elaborate.py::_validate_krb`

**Class 2 -- 3+-file call chains (33 findings).** The test calls a public
entrypoint that lives in NEITHER the test's own file nor the bound
target's file (a third module); that entrypoint calls a public wrapper IN
the target's file, which then reaches the private target. `_cov006`'s
`build_call_graph` is scoped to exactly `(test_file, target_file)`, so the
third file's edge is invisible, and `_cov006_public_wrapper_reachable`'s
rescue only checks whether the literal name the test calls IS a public
symbol in the target's own file -- it never walks through an intermediate
third-file caller to find that public wrapper:
- `tests/test_dup_region.py::TestRegionKernelFindsPartialClone.test_enabled_finds_shared_region_between_otherwise_different_functions -> src/frob/dup/_core.py::_exact_regions` (via `find_clones` in `frob/dup/_pipeline.py` -> `_region_groups` -> `_exact_regions` in a different file)
- `tests/test_lang.py::TestParsePython.test_directive_binds_across_two_blank_lines -> src/frob/lang/_common.py::_find_following_symbol` (via `parse_file`)
- `tests/unit/test_lang_strata.py::TestParseStrata.test_comments_bind_following_symbol -> src/frob/lang/_common.py::_find_following_symbol`
- `tests/unit/test_lang_strata.py::TestParseStrata.test_comment_inside_a_block_binds_as_enclosing -> src/frob/lang/_common.py::_find_enclosing_symbol`
- `tests/test_graph.py::TestBuildIncremental.test_fingerprint_bump_rebuilds -> src/frob/graph/cache.py::_compute_fingerprint` (via `build_graph` in `frob/graph/__init__.py`)
- `tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock.test_scanned_languages_equals_registry_languages -> src/frob/strata/_selfconform.py::_sorted_capability_files`
- `tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock.test_extended_kinds_is_disjoint_from_kind_map -> src/frob/strata/_selfconform.py::_observed_extended_kinds_by_node`
- `tests/unit/strata/test_managed.py::TestManagedGrammar.test_store_managed_marker_elaborates_to_attr -> src/frob/strata/_infra.py::_elaborate_store` (via `elaborate` in `_elaborate.py` -> `elaborate_infra` -> `_elaborate_simple_infra_nodes` -> `_elaborate_store`, all in `_infra.py` except the test's own entrypoint)
- `tests/unit/strata/test_store_code_may.py::TestStoreCodeMayGrammar.test_store_code_glob_elaborates_to_code_attr -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_store_code_may.py::TestStoreCodeMayGrammar.test_store_may_capability_lands_on_node_may -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_infra.py::TestStoreWaivers.test_empty_reason_fails_closed -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_infra.py::TestStoreWaivers.test_whitespace_only_reason_fails_closed -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_infra.py::TestStoreWaivers.test_multi_instance_family_without_sub_target_fails_closed -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_infra.py::TestStoreWaivers.test_multi_instance_family_with_sub_target_elaborates_cleanly -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_litmus_waive_store.py::TestWaiveStoreLitmus.test_matched_store_waiver_suppresses_the_finding -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_litmus_waive_store.py::TestWaiveStoreLitmus.test_matched_store_waiver_is_surfaced_in_waived_with_reason -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_litmus_waive_store.py::TestWaiveStoreLitmus.test_stale_store_waiver_reported_as_syswaive002_gap -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_litmus_waive_store.py::TestWaiveStoreLitmus.test_store_stale_fails -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_litmus_waive_store.py::TestWaiveStoreLitmus.test_store_sub_target_waiver_does_not_suppress_a_different_sub_target -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_store_observability.py::TestStoreObservabilityGrammar.test_store_errors_total_and_panics_become_node_attrs -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/strata/test_store_observability.py::TestStoreOnDeploy.test_store_on_deploy_lands_on_node_deploy_contract -> src/frob/strata/_infra.py::_elaborate_store`
- `tests/unit/test_arch.py::TestDispatchFamilySuppression.test_dispatch_family_no_abstraction_opportunity -> src/frob/arch/_python.py::_is_dispatch_family` (via `analyze_project` in `frob/arch/__init__.py` -> `_python._check_abstraction_opportunities` -> `_is_dispatch_family`, all in `_python.py` except the test's own entrypoint)
- `tests/unit/test_arch.py::TestDispatchFamilySuppression.test_accidental_same_signature_still_flagged -> src/frob/arch/_python.py::_is_dispatch_family`
- `tests/unit/test_arch.py::TestDispatchFamilySuppression.test_accidental_same_signature_still_flagged -> src/frob/arch/_python.py::_near_duplicate_cluster`
- `tests/unit/test_arch.py::TestDispatchFamilySuppression.test_test_file_co_mention_does_not_suppress -> src/frob/arch/_python.py::_is_dispatch_family`
- `tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators.test_generic_signature_unrelated_bodies_not_flagged -> src/frob/arch/_python.py::_check_abstraction_opportunities`
- `tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators.test_generic_signature_unrelated_bodies_not_flagged -> src/frob/arch/_python.py::_signature_is_specific`
- `tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators.test_generic_signature_unrelated_bodies_not_flagged -> src/frob/arch/_python.py::_near_duplicate_cluster`
- `tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators.test_generic_signature_near_duplicate_bodies_still_flagged -> src/frob/arch/_python.py::_check_abstraction_opportunities`
- `tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators.test_generic_signature_near_duplicate_bodies_still_flagged -> src/frob/arch/_python.py::_near_duplicate_cluster`
- `tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators.test_specific_signature_genuine_family_still_flagged -> src/frob/arch/_python.py::_signature_is_specific`
- `tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators.test_specific_signature_genuine_family_still_flagged -> src/frob/arch/_python.py::_check_abstraction_opportunities`
- `tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators.test_generic_signature_only_two_bodies_similar_reports_pair -> src/frob/arch/_python.py::_near_duplicate_cluster`

**Class 3 -- CLI/subprocess integration boundary (2 findings).** The test
drives the CLI in-process (argparse dispatch by subcommand-name string) or
via a subprocess; the private target is reached through argument-parser
dispatch tables, never a literal call the token scanner can see:
- `tests/integration/test_interfaces.py::TestInterfaces.test_version_flag_prints_version_and_exits_zero -> src/frob/__main__.py::_frob_version`
- `tests/system/test_cli_ticket_land.py::TestLandCLI.test_dry_run_reports_clean -> src/frob/app/ticket_runner.py::_land`

**Class 4 -- no Rust call-graph support (7 findings).** `build_call_graph`
(frob.graph.callgraph) only understands the language grammars `frob.lang`
parses far enough to expose `body_tokens`/calls for; Rust's `#[cfg(test)]`
inline `mod tests` functions calling their own module's private `fn`s are
never resolved the same way Python same-file calls are:
- `frob-core/src/lib.rs::tests.is_numeric_literal_rejects_identifiers_and_keywords -> frob-core/src/lib.rs::is_numeric_literal`
- `frob-core/src/lib.rs::tests.is_string_literal_requires_matching_quotes -> frob-core/src/lib.rs::is_string_literal`
- `frob-core/src/lib.rs::tests.anti_unify_identical_trees_has_zero_holes -> frob-core/src/lib.rs::anti_unify_core`
- `frob-core/src/lib.rs::tests.anti_unify_single_leaf_divergence_binds_one_hole -> frob-core/src/lib.rs::anti_unify_core`
- `frob-core/src/lib.rs::tests.anti_unify_arity_mismatch_becomes_a_hole_not_a_crash -> frob-core/src/lib.rs::anti_unify_core`
- `frob-core/src/lib.rs::tests.anti_unify_wildly_different_trees_exceeds_hole_ceiling -> frob-core/src/lib.rs::anti_unify_core`
- `frob-core/src/lib.rs::tests.anti_unify_deterministic_hole_numbering -> frob-core/src/lib.rs::anti_unify_core`

Fix direction per class: Class 1 needs a decorator/dunder-aware rescue (recognize
`@field_validator`/`@model_validator`-decorated methods and dunder protocol
methods as reachable when their OWNING model/class is constructed or used
the matching way in the test, without a literal name call). Class 2 needs
`_cov006_public_wrapper_reachable` to also search the TEST's own file's
direct imports for a public function whose body then reaches the target
transitively (not just requiring the literal called name to itself be a
public symbol in the target's file) -- effectively a 2-hop search: test ->
(any imported public callable) -> ... -> target, instead of just test ->
(public wrapper IN target's file). Class 3 is likely out of scope for a
static call-graph entirely and may just need a documented exemption
(kind=\"integration\"/\"cli\" tagged `frob:tests` edges skip COV006).
Class 4 needs Rust support added to `frob.graph.callgraph`'s language
handling, or a documented exemption for non-Python `frob:tests` targets.