+++
id = "01M48BMS05GVBRPP3B8NMTWA1V"
title = "gob-symbols: evaluate function-local const bindings and namespace-import members in TS const_value"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T10:20:10Z"
updated = "2026-10-22T00:23:06Z"
scope = ["crates/gob-symbols/src/typescript/fold.rs", "crates/gob-symbols/src/typescript/consteval.rs", "crates/gob-symbols/src/typescript/**", "crates/gob-symbols/tests/it/typescript.rs", "docs/reference/fidelity.md", "changelog.d/01M48BMS05GVBRPP3B8NMTWA1V.added.md", "crates/gob-ir/src/const_value.rs", "crates/gob-symbols/src/graph/typescript.rs", "crates/gob-symbols/tests/it/typescript_consteval.rs"]

[[acceptance]]
text = "function-local const bindings and namespace-import members evaluate in TS const_value"
bound = false

[[acceptance]]
text = "A function-local const (incl. one reading module or imported consts) evaluates in TS const_value"
bound = false

[[acceptance]]
text = "A local const shadows module consts and imports, block scopes do not leak, nested functions see outer locals"
bound = false

[[acceptance]]
text = "let/var/parameters stay Unknown and a local const cycle is reported as Cycle"
bound = false

[[acceptance]]
text = "ns.NAME of an import * as ns evaluates (through re-exports); a shadowed ns, default import or missing member stays Unknown"
bound = false
+++

found while working ~C2F4ZMQ. Only module-level const units carry a value to const_value; a const declared inside a component function (const cls = 'a') is a binder with no value node, and ns.NAME through a namespace import is not followed, so both stay Unknown. Lower local const declarators with their value and resolve member access through the module graph.
