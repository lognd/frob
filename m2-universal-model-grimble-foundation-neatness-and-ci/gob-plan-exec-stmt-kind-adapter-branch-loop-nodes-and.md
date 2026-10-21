+++
id = "01M5GE4YWPW8XRWCP5N1A69KMM"
title = "gob-plan exec: stmt kind, adapter branch/loop nodes, and directly-inside through body groups (NEAT031 examples 0 and 1)"
type = "task"
category = "todo"
priority = "medium"
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-21T23:53:37Z"
updated = "2026-10-21T23:53:37Z"
scope = ["crates/gob-plan/src/exec/**", "crates/gob-plan/tests/ten_rules/**"]
+++

found while working ~BZNRM2K. NEAT031 now lowers (count vs knob * count, alt shapes) but its fire/clean examples fail in exec: (1) no KindTest for stmt (python statements are adapter nodes such as expression_statement wrapped in a body Group under the function unit); (2) KindTest::Control only matches Universal Apply/Bind, so python if_statement is not a branch; (3) 'directly inside' is parent-only, but a statement's parent is a body Group, not the function; (4) 'is call' on a statement wrapper should look through expression_statement. Remove NEAT031 0 and 1 from KNOWN_ENGINE_GAPS when done.
