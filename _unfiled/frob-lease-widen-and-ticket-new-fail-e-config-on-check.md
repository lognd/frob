+++
id = "01M68R40J8Y9Z82D0ZGNXAQ460"
title = "frob lease widen and ticket new fail E-CONFIG on [check] output_presenters"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-31T10:29:39Z"
updated = "2026-10-31T10:29:39Z"
+++

Found while working 3K6V7CW: frob lease widen and frob ticket new fail with E-CONFIG 'unknown key output_presenters in [check]' although frob.toml line 26 and gob-check config struct (crates/gob-check/src/config.rs:441) define it. Release binary built from HEAD 1fb6b4d33 rejects it. Likely the [check] key descriptor used by gob-config load omits output_presenters.
