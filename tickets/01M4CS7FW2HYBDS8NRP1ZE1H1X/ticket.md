+++
id = "01M4CS7FW2HYBDS8NRP1ZE1H1X"
title = "gob-macros: ui_rule_attr missing_md fails on Windows because the diagnostic embeds the OS io error text"
type = "bug"
category = "done"
outcome = "done"
priority = "critical"
class = "expedite"
points = 1
reporter = "lognd"
created = "2026-10-08T03:34:35Z"
updated = "2026-10-08T04:24:12Z"
scope = ["crates/gob-macros/**"]

[[acceptance]]
text = "Given the missing_md trybuild case, when the suite runs on Linux and Windows, then both match one snapshot (no OS error text in any gob-macros diagnostic)"
bound = true
+++

CI has been red on experimental since at least 2026-10-07 14:49 (runs 37639920096 .. 37657654375): only the Windows nextest step fails, in gob-macros::ui_rule_attr, case tests/ui_rule/fail/missing_md. The Rule derive's missing-page error interpolates the io::Error Display ('No such file or directory (os error 2)' on Linux, 'The system cannot find the file specified. (os error 2)' on Windows), so the trybuild snapshot can match only one OS. Make compile-time diagnostics platform-stable: map io::ErrorKind to a fixed phrase (for example 'not found') instead of Display, everywhere gob-macros reports an io error, and re-bless the snapshot.
