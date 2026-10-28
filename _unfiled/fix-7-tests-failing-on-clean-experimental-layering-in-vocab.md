+++
id = "01M61QW501Q46SJ8QAY9X5NXA3"
title = "Fix 7 tests failing on clean experimental: layering, in_vocab, lease_widen waits, init/doctor/config_sync"
type = "bug"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-28T17:10:40Z"
updated = "2026-10-28T17:55:27Z"
scope = ["crates/gob-dev/tests/layering.rs", "crates/gob-plan/**", "crates/frob/tests/it/**", "crates/frob/src/**", "crates/frob-cli/**", "crates/frob-check/tests/**", "crates/crunk/tests/**", "crates/crunk/src/**"]

[[acceptance]]
text = "All tests failing in CI run 40729676574 on ubuntu pass: layering, in_vocab, equivalence fixture_b, crunk check_json sibling document, config_sync, doctor_piped, init_twice, lease_widen waits"
bound = false

[[acceptance]]
text = "The windows nextest job failures from the same run are diagnosed and fixed or filed"
bound = false
+++

Found while working ~1G4B9C1; all fail on clean experimental b2daca646f: gob-dev layering (table missing frob-present); gob-plan exec_relations an_in_vocab_op_tests_a_name_against_the_language_vocabulary_classes; frob-cli lease_widen_wait_succeeds_once_the_holder_releases and add_scope_wait_blocks_on_a_held_overlap_and_succeeds_when_it_releases (30s timeouts); cli::config_sync_adds_missing_knobs_once; cli::doctor_piped_is_json_envelope_even_with_cfg001; cli::init_twice_second_is_already_and_changes_nothing (init_frob_toml snapshot / CFG001 knob count).
