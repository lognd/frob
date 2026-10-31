+++
id = "01M6815G9TERKQ7SZ6PJE5NV8X"
title = "Wire top-level phase key into load_spec, DesignSpec, schema and the crunk check envelope"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T03:48:30Z"
updated = "2026-10-31T03:48:30Z"
scope = ["crates/crunk-spec/src/**, crates/crunk-check/src/**"]

[[acceptance]]
text = 'Given phase = "alpha" in crunk.toml, when crunk check runs, then load_spec accepts the key, the envelope reports the phase and the not-applicable rules from phase_profile::report, and the schema documents the key'
bound = false
+++

found while working ~W7FAD5W: read_phase and phase_profile exist but crunk.toml top-level phase is still an unknown key in load_spec and no check path calls report. Also register the ~880G1HE metrics/experiment rule prefixes in phase_profile::LIVE_ONLY_FAMILIES (currently METRIC, EXPERIMENT).
