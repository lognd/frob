+++
id = "01M43MPMEGYAZ33JTP3GRCHKE2"
title = "CLI tests depend on siblings installed on the developer PATH (doctor snapshot gains a crunk warning)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T14:22:19Z"
updated = "2026-10-04T21:17:12Z"
scope = ["crates/frob/tests/attestation.rs", "crates/frob/tests/board.rs", "crates/frob/tests/check_verb.rs", "crates/frob/tests/cli.rs", "crates/frob/tests/close_guards.rs", "crates/frob/tests/common/mod.rs", "crates/frob/tests/cycle.rs", "crates/frob/tests/e2e_init_loop.rs", "crates/frob/tests/first_run.rs", "crates/frob/tests/fragment.rs", "crates/frob/tests/gc.rs", "crates/frob/tests/init_adopt.rs", "crates/frob/tests/lease_widen.rs", "crates/frob/tests/merge_driver_path.rs", "crates/frob/tests/milestone.rs", "crates/frob/tests/pm_config.rs", "crates/frob/tests/pm_wiring.rs", "crates/frob/tests/redact.rs", "crates/frob/tests/release.rs", "crates/frob/tests/release_cut.rs", "crates/frob/tests/release_status.rs", "crates/frob/tests/shared_files.rs", "crates/frob/tests/terminal_lease.rs", "crates/frob/tests/ticket.rs", "crates/frob/tests/ticket_scrub.rs", "crates/frob/tests/ticket_unsynced.rs", "crates/frob/tests/wiring.rs"]

[[acceptance]]
text = "Given a foreign crunk executable on the ambient PATH, when the CLI test suite runs, then every snapshot is unchanged"
bound = true
+++

frob-cli test doctor_piped_is_json_envelope_even_with_cfg001 fails on a machine where the Python crunk is on PATH: sibling discovery finds it and the snapshot gains a warning. Tests that run the frob binary must be hermetic about siblings: the test harness sets PATH (and any sibling discovery env) to a controlled directory, so results never depend on what the developer has installed. Apply it in the shared test support used by the CLI tests, not per test, and add a test that a foreign crunk on the ambient PATH does not change doctor output.
