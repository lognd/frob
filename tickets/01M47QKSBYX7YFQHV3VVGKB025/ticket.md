+++
id = "01M47QKSBYX7YFQHV3VVGKB025"
title = "gob-symbols: lower JSX/TSX to markup and inline style objects to style"
type = "story"
category = "in-progress"
priority = "high"
points = 8
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T04:30:09Z"
updated = "2026-10-06T08:23:54Z"
scope = ["crates/gob-symbols/**", "docs/reference/fidelity.md"]

[[links]]
kind = "blocked-by"
target = "01M43ARXMH7RJ63G8096KKJF80"

[[links]]
kind = "blocked-by"
target = "01M47QKDM2J0EKW2TYH4N35GSV"

[[acceptance]]
text = "fixtures under crates/gob-symbols cover intrinsic, component, spread, conditional and mapped JSX with expected markup snapshots"
bound = true

[[acceptance]]
text = "a component usage is an apply edge from the using unit to the component unit in the call graph"
bound = true

[[acceptance]]
text = "inline style objects produce style declarations with Known values for literal properties and Unknown for computed ones"
bound = true
+++

language-engines.md sections 2 and 3. The TS/TSX adapter lowers JSX elements to markup: intrinsic tags as apply(kind=element) with a literal head, component tags (capitalised or member expressions) with a ref head resolved through the scope graph so component use is a call edge, attributes as named args with const_value values, spreads at status May, fragments, conditional and mapped children as group. style={{...}} objects lower to style declarations; CSS-in-JS template literals tagged css become a region island in css. Replaces the extraction half of ~8JGRZY3.
