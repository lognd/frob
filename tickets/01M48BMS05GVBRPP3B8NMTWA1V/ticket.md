+++
id = "01M48BMS05GVBRPP3B8NMTWA1V"
title = "gob-symbols: evaluate function-local const bindings and namespace-import members in TS const_value"
type = "task"
category = "todo"
priority = "medium"
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T10:20:10Z"
updated = "2026-10-06T10:20:10Z"
scope = ["crates/gob-symbols/src/typescript/fold.rs", "crates/gob-symbols/src/typescript/consteval.rs"]
+++

found while working ~C2F4ZMQ. Only module-level const units carry a value to const_value; a const declared inside a component function (const cls = 'a') is a binder with no value node, and ns.NAME through a namespace import is not followed, so both stay Unknown. Lower local const declarators with their value and resolve member access through the module graph.
