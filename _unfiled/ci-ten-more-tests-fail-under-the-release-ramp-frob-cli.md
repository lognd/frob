+++
id = "01M5X65SGY3D8E9FKHZAG0CHE0"
title = "CI: ten more tests fail under the release ramp (frob-cli milestone/redact/release_cut, frob-land, grimble summary/verbs/ack)"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-26T22:44:24Z"
updated = "2026-10-26T22:53:51Z"
scope = ["crates/grimble/tests/**", "crates/frob-land/tests/**", "crates/frob/tests/**"]

[[acceptance]]
text = "Given the ten tests failing in CI run 40409008413, when nextest runs -p grimble -p frob-land -p frob-cli, then they pass with the ramp active in the product and ramp=false or ramp-aware expectations in fixtures"
bound = false
+++

CI run 40409008413 on 92a146815e, ubuntu and windows: frob-cli::it milestone::pm_strict_escalates_pm001_to_error, redact::check_flags_and_doctor_fix_repairs, release_cut::adopt_records_hand_made_tags_as_an_adopted_cut_and_clears_rel001; frob-land::land a_release_finding_the_ticket_introduces_refuses and a_repository_level_finding_on_the_base_does_not_block_an_unrelated_ticket; grimble::ack ack_writes_the_lock_and_check_reports_contract_skew_after_a_producer_edit, grimble::summary small_model_lists_each_node, summary_without_json_still_runs, summary_of_a_large_model_is_compact, grimble::verbs a_model_error_exits_one_and_the_finding_is_in_the_document. Same cause as ~F3D43SD: ~B3EMY2Z ramp reports rules new in 0.532.0 at warn (exit 0, counts differ). Fix fixtures (grimble.toml/frob.toml [rules] ramp = false) or expectations; product behaviour stays. Check whether the grimble.toml and frob.toml loaders accept a [rules] table.
