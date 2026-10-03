+++
id = "01M41RK1G648EJJNRK4G5RJY40"
title = "Nine tests fail on windows-latest: merge driver, command allowlist, trust config dir and paths on Windows"
type = "bug"
category = "in-progress"
priority = "critical"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T20:51:46Z"
updated = "2026-10-03T20:52:08Z"
scope = ["crates/frob/src/init.rs", "crates/gob-trust/src/**", "crates/gob-cli/tests/root.rs", "crates/gob-trust/tests/trust.rs", "crates/frob-tests/tests/selection.rs", "crates/frob/tests/e2e_init_loop.rs", "crates/frob/tests/close_guards.rs", "crates/frob/tests/ticket.rs", "crates/frob/tests/pm_wiring.rs"]

[[acceptance]]
text = "Given the windows-latest CI job, when cargo nextest run --profile ci runs, then all tests pass"
bound = false

[[acceptance]]
text = "Given frob init on Windows, when a ledger merge happens, then git runs the frob merge driver and the merge succeeds"
bound = false
+++

CI run https://github.com/lognd/frob/actions/runs/37151892875 (2026-10-03), windows-latest: 1270 tests, 9 failed. These are product bugs on a release target (x86_64-pc-windows-msvc is one of the five), not test noise; fix the product where the product is wrong and the test where the test is non-portable, and say which for each:

1. frob-cli::cli init_twice_second_is_already_and_changes_nothing: init_frob_toml snapshot differs at line 142 (probably a path or line ending written by init).
2. frob-cli::close_guards the_running_frob_is_an_allowed_command_tool_without_listing_it: evidence add --provider command --ref "D:\a\frob\frob\target\debug/frob.exe --version" exits 3; the running-executable allowlist match fails on a Windows path (backslashes, .exe, mixed separators).
3. frob-cli::e2e_init_loop loop_on_main and loop_on_trunk: panic at e2e_init_loop.rs:238.
4. frob-cli::pm_wiring concurrent_milestone_edits_... and frob-cli::ticket merge_driver_unions_events_...: git merge exits 1; the ledger merge driver does not run on Windows. init writes merge.frob-ledger.driver as the running executable's absolute path; on Windows that path has backslashes and spaces that git's driver command line (run through sh) mangles. Write a form git for Windows executes (forward slashes, quoted), and test it on the Windows target.
5. frob-tests::selection test_verb_runs_the_selection_and_appends_evidence_in_a_leased_worktree: panic at selection.rs:283.
6. gob-cli::root cwd_flag_is_validated_and_applied: the test compares a path string with '/'; make the comparison path-aware (or the product prints a normalized path).
7. gob-trust::trust path_resolution: NoConfigDir; the trust store's config dir lookup has no Windows branch (use %APPDATA% / the platform config dir the rest of frob uses).

Reproduce what you can on the Linux host with the x86_64-pc-windows-gnu target (clippy works there; tests cannot run). For runtime behaviour, read the Windows log of the run above (gh run view 37151892875 --log-failed) for the full panic messages. Do not use ~/bin/winrun or winsync.
