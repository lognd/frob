+++
id = "01M43MPMEGYAZ33JTP3GRCHKE2"
title = "CLI tests depend on siblings installed on the developer PATH (doctor snapshot gains a crunk warning)"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T14:22:19Z"
updated = "2026-10-04T14:22:19Z"

[[acceptance]]
text = "Given a foreign crunk executable on the ambient PATH, when the CLI test suite runs, then every snapshot is unchanged"
bound = false
+++

frob-cli test doctor_piped_is_json_envelope_even_with_cfg001 fails on a machine where the Python crunk is on PATH: sibling discovery finds it and the snapshot gains a warning. Tests that run the frob binary must be hermetic about siblings: the test harness sets PATH (and any sibling discovery env) to a controlled directory, so results never depend on what the developer has installed. Apply it in the shared test support used by the CLI tests, not per test, and add a test that a foreign crunk on the ambient PATH does not change doctor output.
