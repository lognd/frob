+++
id = "01M55VDSM0FWP78JG2RMQ7HJTJ"
title = "ci.yml: fold Windows isolated-tool step pairs into one matrix-variable step per check (audit M18)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-17T21:14:00Z"
updated = "2026-10-17T21:14:00Z"
scope = [".github/workflows/ci.yml", "crates/gob-dev/tests/ci_parity.rs"]
+++

found while working ~BN7DCP3: ci_parity.rs requires literal cargo dev / cargo dev-isolated prefixes, so folding needs the test updated together
