---
id: T-0785
title: 'dup: normalize error-channel (Result vs Optional vs raise) before similarity
  compare'
state: done
kind: feature
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/**
- tests/test_dup.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup.py::TestErrorChannelNormalization::test_err_and_none_collapse_to_the_same_marker
- tests/test_dup.py::TestErrorChannelNormalization::test_ok_unwraps_to_the_bare_payload
- tests/test_dup.py::TestErrorChannelNormalization::test_raise_collapses_to_the_same_marker_as_err_and_none
- tests/test_dup.py::TestErrorChannelNormalization::test_a_genuinely_different_return_value_is_not_collapsed
- tests/test_dup.py::TestErrorChannelNormalization::test_nested_err_argument_parens_do_not_confuse_the_close_paren_scan
- tests/test_dup.py::TestErrorChannelDupPairing::test_result_and_optional_git_common_dir_register_as_a_duplicate_group
- tests/test_dup.py::TestErrorChannelNormalizationDoesNotOverFire::test_genuinely_different_logic_does_not_falsely_pair
designated_repro_test: null
acceptance:
- text: GIVEN two functions identical except one returns Result and the other Optional-with-None
    WHEN the dup scan runs THEN they register as a duplicate group; GIVEN genuinely
    different logic THEN no false pair
  evidence:
  - tests/test_dup.py::TestErrorChannelNormalization::test_err_and_none_collapse_to_the_same_marker
  - tests/test_dup.py::TestErrorChannelNormalization::test_ok_unwraps_to_the_bare_payload
  - tests/test_dup.py::TestErrorChannelNormalization::test_raise_collapses_to_the_same_marker_as_err_and_none
  - tests/test_dup.py::TestErrorChannelNormalization::test_a_genuinely_different_return_value_is_not_collapsed
  - tests/test_dup.py::TestErrorChannelNormalization::test_nested_err_argument_parens_do_not_confuse_the_close_paren_scan
  - tests/test_dup.py::TestErrorChannelDupPairing::test_result_and_optional_git_common_dir_register_as_a_duplicate_group
  - tests/test_dup.py::TestErrorChannelNormalizationDoesNotOverFire::test_genuinely_different_logic_does_not_falsely_pair
threat: null
component: null
---
Audit M3 gate-direction: the triplicated git-common-dir resolver slipped under DUP's similarity threshold purely on error-channel shape. Normalize Ok/Err vs return-None vs raise into a canonical form before comparing.