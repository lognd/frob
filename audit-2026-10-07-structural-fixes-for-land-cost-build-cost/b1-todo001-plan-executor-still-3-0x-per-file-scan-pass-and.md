+++
id = "01M70W9EY0YN8GJVW455DTPPQN"
title = "B1 TODO001: plan executor still 3.0x per file; scan pass and allocation dominate"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-11-09T19:24:18Z"
updated = "2026-11-12T12:30:10Z"
scope = ["crates/gob-plan/src/exec/**"]
+++

Follow-up of ~W0Q305Z. FastMap for matchers/kinds/edges/side was neutral (3.03x to 3.02x). Profile of b1/TODO001/plan is flat: Eval::scan full-node pass (is_opaque cache misses) 6-10%, libc malloc 19%, regex lazy DFA 6%, verdict join/clone 2%. Next: avoid the whole-term scan (lazy hidden/domains or kind index), cut per-node Verdict/acc clones in enumerate, pool allocations.
