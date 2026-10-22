//! Replay the captured Python end-to-end scenarios (E2E-01..59) against the Rust crunk.
//!
//! One test per scenario. Each replays the scenario step by step (see `replay`) and requires every
//! exit-code or file-effect difference from the Python golden to be listed, with a reason, in
//! `divergences.toml`; a listed difference that no longer occurs fails the test. `audit` checks the
//! mapping table (`mapping.toml`) against the captured Python nodes and these test functions.

// frob:ticket 01M43AVKZWSTQRGWR6YPXH7THX

use std::collections::BTreeSet;

mod audit;
mod divergences;
mod replay;

/// Replay `scenario` and fail on any unlisted difference or stale divergence entry.
fn check(scenario: &str) {
    let problems = divergences::judge(scenario, &replay::replay(scenario));
    assert!(problems.is_empty(), "{scenario}: {}", problems.join("; "));
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_01_init_init_default_preset_then_check_clean() {
    check("e2e_01_init/init_default_preset_then_check_clean");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_01_init_init_mono_preset_then_check_clean() {
    check("e2e_01_init/init_mono_preset_then_check_clean");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_01_init_reinit_without_force_exits_2() {
    check("e2e_01_init/reinit_without_force_exits_2");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_01_init_reinit_with_force_exits_0() {
    check("e2e_01_init/reinit_with_force_exits_0");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_02_color_near_accent_color_flagged_and_fixed() {
    check("e2e_02_color/near_accent_color_flagged_and_fixed");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_03_spacing_space001_warns_by_default_then_errors_when_releveled() {
    check("e2e_03_spacing/space001_warns_by_default_then_errors_when_releveled");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_03_spacing_fix_snaps_near_value_leaves_far_value() {
    check("e2e_03_spacing/fix_snaps_near_value_leaves_far_value");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_04_org_stray_file_is_org001() {
    check("e2e_04_org/stray_file_is_org001");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_04_org_bad_case_and_missing_prefix_are_org002_and_org003() {
    check("e2e_04_org/bad_case_and_missing_prefix_are_org002_and_org003");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_05_tokens_edit_accent_drifts_then_regenerates_tokens() {
    check("e2e_05_tokens/edit_accent_drifts_then_regenerates_tokens");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_06_waiver_waiver_with_reason_silences_and_counts_waived() {
    check("e2e_06_waiver/waiver_with_reason_silences_and_counts_waived");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_06_waiver_waiver_without_reason_is_waive001() {
    check("e2e_06_waiver/waiver_without_reason_is_waive001");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_07_json_exit_codes_json_clean_tree_exits_0_and_parses() {
    check("e2e_07_json_exit_codes/json_clean_tree_exits_0_and_parses");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_07_json_exit_codes_json_violating_tree_exits_1_with_rule_path_line() {
    check("e2e_07_json_exit_codes/json_violating_tree_exits_1_with_rule_path_line");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_07_json_exit_codes_corrupt_crunk_toml_exits_2() {
    check("e2e_07_json_exit_codes/corrupt_crunk_toml_exits_2");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_08_contrast_low_contrast_role_pair_is_contrast001_with_ratio() {
    check("e2e_08_contrast/low_contrast_role_pair_is_contrast001_with_ratio");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_09_map_map_text_lists_component_and_flags_stray() {
    check("e2e_09_map/map_text_lists_component_and_flags_stray");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_09_map_map_json_round_trips_pinned_shape() {
    check("e2e_09_map/map_json_round_trips_pinned_shape");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_10_alpha_exact_rgb_translucent_literal_passes_untouched() {
    check("e2e_10_alpha/exact_rgb_translucent_literal_passes_untouched");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_10_alpha_near_translucent_literal_fixes_to_color_mix_preserving_alpha() {
    check("e2e_10_alpha/near_translucent_literal_fixes_to_color_mix_preserving_alpha");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_10_alpha_far_translucent_literal_reported_not_fixed() {
    check("e2e_10_alpha/far_translucent_literal_reported_not_fixed");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_11_stacks_declared_stacks_pass_check_and_export_tokens() {
    check("e2e_11_stacks/declared_stacks_pass_check_and_export_tokens");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_12_ungoverned_outside_css_flagged_as_org005() {
    check("e2e_12_ungoverned/outside_css_flagged_as_org005");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_12_ungoverned_org_ignore_glob_silences_exactly_it() {
    check("e2e_12_ungoverned/org_ignore_glob_silences_exactly_it");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_12_ungoverned_map_still_shows_only_governed_files() {
    check("e2e_12_ungoverned/map_still_shows_only_governed_files");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_13_prefixes_empty_color_prefix_exported_accepted_and_fixed() {
    check("e2e_13_prefixes/empty_color_prefix_exported_accepted_and_fixed");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_14_entry_entry_file_no_org001_and_layer_color_located() {
    check("e2e_14_entry/entry_file_no_org001_and_layer_color_located");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_14_entry_map_shows_entry_group() {
    check("e2e_14_entry/map_shows_entry_group");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_15_output_check_paths_are_root_relative_terminal_and_json() {
    check("e2e_15_output/check_paths_are_root_relative_terminal_and_json");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_15_output_fix_output_path_is_root_relative() {
    check("e2e_15_output/fix_output_path_is_root_relative");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_15_output_map_output_paths_are_root_relative() {
    check("e2e_15_output/map_output_paths_are_root_relative");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_15_output_check_contrast_clean_exits_0() {
    check("e2e_15_output/check_contrast_clean_exits_0");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_15_output_check_contrast_failing_pair_exits_1() {
    check("e2e_15_output/check_contrast_failing_pair_exits_1");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_16_query_find_text_and_json() {
    check("e2e_16_query/find_text_and_json");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_16_query_component_card() {
    check("e2e_16_query/component_card");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_16_query_component_unknown_name_exits_2() {
    check("e2e_16_query/component_unknown_name_exits_2");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_16_query_dupes_finds_planted_pair() {
    check("e2e_16_query/dupes_finds_planted_pair");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_16_query_unused_finds_planted_token() {
    check("e2e_16_query/unused_finds_planted_token");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_16_query_uses_leading_dashes_optional() {
    check("e2e_16_query/uses_leading_dashes_optional");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_16_query_color_nearest_palette_entries() {
    check("e2e_16_query/color_nearest_palette_entries");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_16_query_color_unparseable_value_exits_2() {
    check("e2e_16_query/color_unparseable_value_exits_2");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_16_query_violations_filtered_by_rule() {
    check("e2e_16_query/violations_filtered_by_rule");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_16_query_query_with_no_subcommand_exits_2() {
    check("e2e_16_query/query_with_no_subcommand_exits_2");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_17_cache_warm_run_byte_identical_to_cold() {
    check("e2e_17_cache/warm_run_byte_identical_to_cold");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_17_cache_stylesheet_edit_invalidates_cache() {
    check("e2e_17_cache/stylesheet_edit_invalidates_cache");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_17_cache_crunk_toml_edit_invalidates_cache() {
    check("e2e_17_cache/crunk_toml_edit_invalidates_cache");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_17_cache_no_cache_bypasses_reads_but_still_refreshes() {
    check("e2e_17_cache/no_cache_bypasses_reads_but_still_refreshes");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_18_19_schema_missing_section_names_offender_exit_2_no_verbose() {
    check("e2e_18_19_schema/missing_section_names_offender_exit_2_no_verbose");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_18_19_schema_bad_class_case_names_offender_exit_2_no_verbose() {
    check("e2e_18_19_schema/bad_class_case_names_offender_exit_2_no_verbose");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_18_19_schema_minimal_spec_loads_with_documented_defaults() {
    check("e2e_18_19_schema/minimal_spec_loads_with_documented_defaults");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_20_21_ux_tokens_format_css_previews_without_writing() {
    check("e2e_20_21_ux/tokens_format_css_previews_without_writing");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_20_21_ux_fix_dry_run_names_unfixable_remainder() {
    check("e2e_20_21_ux/fix_dry_run_names_unfixable_remainder");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_20_21_ux_fix_with_applied_fixes_still_names_unfixable_remainder() {
    check("e2e_20_21_ux/fix_with_applied_fixes_still_names_unfixable_remainder");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_22_floors_floor_role_passes_plain_role_fails_terminal() {
    check("e2e_22_floors/floor_role_passes_plain_role_fails_terminal");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_22_floors_floor_role_json_field_parses() {
    check("e2e_22_floors/floor_role_json_field_parses");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_23_header_configured_header_verbatim_and_family_quoted() {
    check("e2e_23_header/configured_header_verbatim_and_family_quoted");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_24_25_jsx_e2e_24_jsx_style_props_judged_never_fixable() {
    check("e2e_24_25_jsx/e2e_24_jsx_style_props_judged_never_fixable");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_24_25_jsx_e2e_25_tw001_arbitrary_utilities_and_tw002_undefined_mapping() {
    check("e2e_24_25_jsx/e2e_25_tw001_arbitrary_utilities_and_tw002_undefined_mapping");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_26_tsx_inventory_query_component_cards_a_jsx_component() {
    check("e2e_26_tsx_inventory/query_component_cards_a_jsx_component");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_26_tsx_inventory_query_find_ranks_the_jsx_component() {
    check("e2e_26_tsx_inventory/query_find_ranks_the_jsx_component");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_26_tsx_inventory_map_shows_jsx_group_terminal_and_json() {
    check("e2e_26_tsx_inventory/map_shows_jsx_group_terminal_and_json");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_26_tsx_inventory_cache_key_changes_when_jsx_source_or_tailwind_config_changes() {
    check("e2e_26_tsx_inventory/cache_key_changes_when_jsx_source_or_tailwind_config_changes");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_27_theme_bare_tokens_writes_tailwind_file_deterministically() {
    check("e2e_27_theme/bare_tokens_writes_tailwind_file_deterministically");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_27_theme_palette_edit_changes_tailwind_file() {
    check("e2e_27_theme/palette_edit_changes_tailwind_file");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_27_theme_hand_edited_tailwind_file_raises_tokens001_naming_it() {
    check("e2e_27_theme/hand_edited_tailwind_file_raises_tokens001_naming_it");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_27_theme_format_tailwind_previews_without_writing() {
    check("e2e_27_theme/format_tailwind_previews_without_writing");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_27_theme_hand_edited_json_file_raises_tokens001_naming_it() {
    check("e2e_27_theme/hand_edited_json_file_raises_tokens001_naming_it");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_28_report_report_json_v2_schema_clean_tree() {
    check("e2e_28_report/report_json_v2_schema_clean_tree");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_28_report_report_markdown_and_json_agree_on_violating_tree() {
    check("e2e_28_report/report_markdown_and_json_agree_on_violating_tree");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_28_report_report_deterministic_on_unchanged_tree() {
    check("e2e_28_report/report_deterministic_on_unchanged_tree");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_28_report_report_and_contrast_mutually_exclusive() {
    check("e2e_28_report/report_and_contrast_mutually_exclusive");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_29_utility_first_utility_first_tree_checks_clean() {
    check("e2e_29_utility_first/utility_first_tree_checks_clean");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_29_utility_first_utility_first_tree_planted_drift_still_fires() {
    check("e2e_29_utility_first/utility_first_tree_planted_drift_still_fires");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_29_utility_first_same_tree_under_buckets_model_shows_org001() {
    check("e2e_29_utility_first/same_tree_under_buckets_model_shows_org001");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_30_suggested_check_json_carries_suggested_tokens() {
    check("e2e_30_suggested/check_json_carries_suggested_tokens");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_30_suggested_report_json_carries_suggested_tokens() {
    check("e2e_30_suggested/report_json_carries_suggested_tokens");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_31_preview_diff_e2e_31_preview_every_entry_and_step_deterministic() {
    check("e2e_31_preview_diff/e2e_31_preview_every_entry_and_step_deterministic");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_31_preview_diff_e2e_31_diff_shows_exactly_the_edited_delta() {
    check("e2e_31_preview_diff/e2e_31_diff_shows_exactly_the_edited_delta");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_32_explain_e2e_32_explain_prints_value_group_defined_in_and_sites() {
    check("e2e_32_explain/e2e_32_explain_prints_value_group_defined_in_and_sites");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_33_orphan_e2e_33_scaffold_states_path_base_rule() {
    check("e2e_33_orphan/e2e_33_scaffold_states_path_base_rule");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_33_orphan_e2e_33_orphan_warning_on_write() {
    check("e2e_33_orphan/e2e_33_orphan_warning_on_write");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_33_orphan_e2e_33_orphan_warning_on_check() {
    check("e2e_33_orphan/e2e_33_orphan_warning_on_check");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_33_orphan_e2e_33_no_warning_without_stale_copy() {
    check("e2e_33_orphan/e2e_33_no_warning_without_stale_copy");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_34_explain_jsx_e2e_34_explain_lists_jsx_utility_only_site() {
    check("e2e_34_explain_jsx/e2e_34_explain_lists_jsx_utility_only_site");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_35_color_flag_preview_color_flag_carries_ansi_when_piped() {
    check("e2e_35_color_flag/preview_color_flag_carries_ansi_when_piped");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_35_color_flag_preview_unflagged_piped_run_stays_plain() {
    check("e2e_35_color_flag/preview_unflagged_piped_run_stays_plain");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_35_color_flag_preview_no_color_env_wins_over_color_flag() {
    check("e2e_35_color_flag/preview_no_color_env_wins_over_color_flag");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_36_keyspace_e2e_36_collision_warning_on_write() {
    check("e2e_36_keyspace/e2e_36_collision_warning_on_write");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_36_keyspace_e2e_36_collision_warning_on_check() {
    check("e2e_36_keyspace/e2e_36_collision_warning_on_check");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_36_keyspace_e2e_36_namespace_keys_emits_prefixed_keys_and_no_warning() {
    check("e2e_36_keyspace/e2e_36_namespace_keys_emits_prefixed_keys_and_no_warning");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_36_keyspace_e2e_36_no_warning_without_tailwind_file() {
    check("e2e_36_keyspace/e2e_36_no_warning_without_tailwind_file");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_37_alpha_channels_e2e_37_non_alpha_theme_mapping_fires_tw003() {
    check("e2e_37_alpha_channels/e2e_37_non_alpha_theme_mapping_fires_tw003");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_37_alpha_channels_e2e_37_alpha_capable_theme_mapping_is_silent() {
    check("e2e_37_alpha_channels/e2e_37_alpha_capable_theme_mapping_is_silent");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_37_alpha_channels_e2e_37_alpha_channels_emits_rgb_triplets_and_alpha_capable_theme() {
    check("e2e_37_alpha_channels/e2e_37_alpha_channels_emits_rgb_triplets_and_alpha_capable_theme");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_38_ts_constants_ts_class_constant_e2e() {
    check("e2e_38_ts_constants/ts_class_constant_e2e");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_39_report_unused_report_json_unused_tokens_matches_query_unused() {
    check("e2e_39_report_unused/report_json_unused_tokens_matches_query_unused");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_39_report_unused_report_markdown_unused_section() {
    check("e2e_39_report_unused/report_markdown_unused_section");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_40_channel_triplets_channel_triplet_and_exact_rgba_both_yield_color001() {
    check("e2e_40_channel_triplets/channel_triplet_and_exact_rgba_both_yield_color001");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_40_channel_triplets_glass_panel_definition_sites_both_yield_org004() {
    check("e2e_40_channel_triplets/glass_panel_definition_sites_both_yield_org004");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_41_sizes_e2e_41_size001_warns_and_fix_snaps_in_css_only() {
    check("e2e_41_sizes/e2e_41_size001_warns_and_fix_snaps_in_css_only");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_41_sizes_e2e_41_max_width_exempt() {
    check("e2e_41_sizes/e2e_41_max_width_exempt");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_41_sizes_e2e_41_spacing_fallback_when_sizes_undeclared() {
    check("e2e_41_sizes/e2e_41_spacing_fallback_when_sizes_undeclared");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_42_43_44_viewport_e2e_42_bp001_media_query_viewport() {
    check("e2e_42_43_44_viewport/e2e_42_bp001_media_query_viewport");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_42_43_44_viewport_e2e_42_bp_family_silent_with_no_breakpoints() {
    check("e2e_42_43_44_viewport/e2e_42_bp_family_silent_with_no_breakpoints");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_42_43_44_viewport_e2e_43_bp002_responsive_variant_missing_base() {
    check("e2e_42_43_44_viewport/e2e_43_bp002_responsive_variant_missing_base");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_42_43_44_viewport_e2e_44_bp003_overflow_width_via_tailwind_default() {
    check("e2e_42_43_44_viewport/e2e_44_bp003_overflow_width_via_tailwind_default");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_45_selfmap_e2e_45_selfmap_explain_and_unused() {
    check("e2e_45_selfmap/e2e_45_selfmap_explain_and_unused");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_45_selfmap_e2e_45_selfmap_both_knobs_explain_and_unused() {
    check("e2e_45_selfmap/e2e_45_selfmap_both_knobs_explain_and_unused");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_46_explain_hardened_e2e_46_explain_rgb_companion_answers_channel_form() {
    check("e2e_46_explain_hardened/e2e_46_explain_rgb_companion_answers_channel_form");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_46_explain_hardened_e2e_46_explain_nonsense_exits_2_clean() {
    check("e2e_46_explain_hardened/e2e_46_explain_nonsense_exits_2_clean");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_47_optional_dims_e2e_47_minimal_spec_without_layers_and_radii_loads_and_checks() {
    check("e2e_47_optional_dims/e2e_47_minimal_spec_without_layers_and_radii_loads_and_checks");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_47_optional_dims_e2e_47_radius001_and_layer001_stay_silent() {
    check("e2e_47_optional_dims/e2e_47_radius001_and_layer001_stay_silent");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_47_optional_dims_e2e_47_tokens_emit_no_radius_or_layer_tokens() {
    check("e2e_47_optional_dims/e2e_47_tokens_emit_no_radius_or_layer_tokens");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_48_semantic_drift_formatter_rewrap_of_json_artifacts_passes_check() {
    check("e2e_48_semantic_drift/formatter_rewrap_of_json_artifacts_passes_check");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_48_semantic_drift_value_edit_in_json_artifact_still_fails_check() {
    check("e2e_48_semantic_drift/value_edit_in_json_artifact_still_fails_check");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_48_semantic_drift_tokens_css_byte_edit_still_fails_check() {
    check("e2e_48_semantic_drift/tokens_css_byte_edit_still_fails_check");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_49_50_exclusivity_e2e_49_tw004_default_color_denylist() {
    check("e2e_49_50_exclusivity/e2e_49_tw004_default_color_denylist");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_49_50_exclusivity_e2e_50_tw005_default_scale_key_bypass() {
    check("e2e_49_50_exclusivity/e2e_50_tw005_default_scale_key_bypass");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_51_sizes_e2e_51_size_prefixes_bypass_default_scale() {
    check("e2e_51_sizes/e2e_51_size_prefixes_bypass_default_scale");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_51_sizes_e2e_51_size_export_and_theme_and_suggested_token() {
    check("e2e_51_sizes/e2e_51_size_export_and_theme_and_suggested_token");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_52_config_e2e_52_borrowed_spec_judges_tree_with_no_crunk_toml() {
    check("e2e_52_config/e2e_52_borrowed_spec_judges_tree_with_no_crunk_toml");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_53_borrower_e2e_53_absent_css_root_borrower_still_runs_jsx() {
    check("e2e_53_borrower/e2e_53_absent_css_root_borrower_still_runs_jsx");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_54_pathmode_e2e_54_path_scoped_run_matches_repo_wide_findings() {
    check("e2e_54_pathmode/e2e_54_path_scoped_run_matches_repo_wide_findings");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_55_cache_home_second_run_hits_and_project_tree_gains_no_entries() {
    check("e2e_55_cache_home/second_run_hits_and_project_tree_gains_no_entries");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_55_cache_home_without_override_resolves_under_xdg_fallback() {
    check("e2e_55_cache_home/without_override_resolves_under_xdg_fallback");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_56_57_58_honesty_e2e_56_outside_root_path_exits_2() {
    check("e2e_56_57_58_honesty/e2e_56_outside_root_path_exits_2");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_56_57_58_honesty_e2e_56_missing_spec_exits_2() {
    check("e2e_56_57_58_honesty/e2e_56_missing_spec_exits_2");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_56_57_58_honesty_e2e_57_cache_ls_and_prune() {
    check("e2e_56_57_58_honesty/e2e_57_cache_ls_and_prune");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_56_57_58_honesty_e2e_57_cache_prune_all() {
    check("e2e_56_57_58_honesty/e2e_57_cache_prune_all");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_56_57_58_honesty_e2e_58_explain_unknown_no_near_candidates() {
    check("e2e_56_57_58_honesty/e2e_58_explain_unknown_no_near_candidates");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_56_57_58_honesty_e2e_58_explain_unknown_near_miss_still_shows_closest() {
    check("e2e_56_57_58_honesty/e2e_58_explain_unknown_near_miss_still_shows_closest");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_56_57_58_honesty_e2e_58_map_all_empty_prints_note() {
    check("e2e_56_57_58_honesty/e2e_58_map_all_empty_prints_note");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_59_root_locator_borrowed_root_defaults_wrong_and_root_flag_fixes_it() {
    check("e2e_59_root_locator/borrowed_root_defaults_wrong_and_root_flag_fixes_it");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn e2e_59_root_locator_plain_in_project_run_prints_no_locator() {
    check("e2e_59_root_locator/plain_in_project_run_prints_no_locator");
}

const MAPPING: &str = include_str!("mapping.toml");
const SOURCES: [&str; 2] = [include_str!("main.rs"), include_str!("../int/main.rs")];

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn mapping_audit_passes() {
    let (nodes, ids) = audit::required();
    assert!(
        nodes.len() > 100,
        "the captured corpus lists its python tests"
    );
    let problems = audit::audit(MAPPING, &SOURCES, &nodes, &ids);
    assert!(problems.is_empty(), "{}", problems.join("\n"));
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn audit_fails_when_a_counterpart_is_removed() {
    let (nodes, ids) = audit::required();
    let renamed = SOURCES[0].replacen(
        "fn e2e_01_init_init_default_preset_then_check_clean(",
        "fn gone(",
        1,
    );
    let problems = audit::audit(MAPPING, &[renamed.as_str(), SOURCES[1]], &nodes, &ids);
    assert!(
        problems
            .iter()
            .any(|p| p
                .contains("missing rust test e2e_01_init_init_default_preset_then_check_clean")),
        "{problems:?}"
    );
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn audit_fails_on_an_unmapped_node_or_empty_reason() {
    let (nodes, ids) = audit::required();
    let cut = MAPPING
        .split("\n[[row]]")
        .take(2)
        .collect::<Vec<_>>()
        .join("\n[[row]]");
    let problems = audit::audit(&cut, &SOURCES, &nodes, &ids);
    assert!(
        problems.iter().any(|p| p.contains("has no mapping row")),
        "{problems:?}"
    );
    let empty = "[[row]]\nnode = \"n\"\nids = [\"X\"]\ndropped = \" \"\n";
    let problems = audit::audit(empty, &SOURCES, &BTreeSet::new(), &BTreeSet::new());
    assert!(
        problems
            .iter()
            .any(|p| p.contains("non-empty dropped reason")),
        "{problems:?}"
    );
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn divergence_entries_are_reasoned_and_point_at_real_steps() {
    for entry in divergences::load() {
        assert!(
            entry.reason.trim().len() > 20,
            "{} needs a real reason",
            entry.id
        );
        for step in &entry.steps {
            let (scenario, num) = step.split_once('#').expect("step id");
            let file = replay::parity_root()
                .join("fixtures/e2e")
                .join(scenario)
                .join(format!("{num}.step.json"));
            assert!(file.is_file(), "{step} is not a captured step");
        }
    }
}
