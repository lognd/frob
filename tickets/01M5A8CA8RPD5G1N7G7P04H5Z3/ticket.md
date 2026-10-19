+++
id = "01M5A8CA8RPD5G1N7G7P04H5Z3"
title = "grimble tests/verbs.rs: 5 tests fail since CYCLE001/DEAD001/LARGE001 findings appear in check output"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-19T14:17:20Z"
updated = "2026-10-19T14:29:39Z"
scope = ["crates/grimble-arch/**", "crates/grimble-check/**"]

[[acceptance]]
text = "Given an empty or model-only repository, when grimble check runs, then the arch rules are not applicable and the grimble verbs tests pass"
bound = false
+++

check output now carries unresolved arch findings (grimble-arch), so check_json_without_a_model_is_a_valid_empty_sibling_document, an_accept_clause_parks_its_finding_and_is_listed, init_twice_is_idempotent, the_binary_prints_exactly_one_envelope_line_on_stdout and a_model_error_exits_one_and_the_finding_is_in_the_document fail. Fix the product (arch findings must not fire on a model-only/empty repo) or the tests, whichever is the real regression.
