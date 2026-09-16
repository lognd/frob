---
id: T-4505
title: Wire a C# capability resolver into _capability_scan.py
state: dropped
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4506
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_csharp.py
- src/frob/vet/_capability_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add src/frob/vet/_capability_csharp.py (binding-aware resolver, modeled on _capability_c.py/_capability_kotlin.py) that resolves 'using' directives (including aliases and 'using static'), fully-qualified calls, and namespace imports to capability findings, replacing raw-needle-only matching from _capability_registry/_dangerous_ops_bash_csharp.py. Wire it into src/frob/vet/_capability_scan.py's per-language import/dispatch table alongside the other five languages.

GIVEN a .cs file with 'using System.IO;' and a File.WriteAllText call, WHEN frob vet scans it, THEN it reports fs.write with the resolved binding, not just a raw needle match.
GIVEN 'using IO = System.IO;' (an alias) and a call through the alias, WHEN scanned, THEN the resolver follows the alias to the same capability.
GIVEN 'using static System.Console;' and a bare WriteLine call, WHEN scanned, THEN the static-using resolves to the correct fully-qualified symbol.
GIVEN a .cs file with no dangerous APIs, WHEN scanned, THEN zero findings (no false positives from the wired resolver).

## Drop reason
- 2026-09-16: duplicate promoted copy of the C# resolver draft; the work landed as T-4536
