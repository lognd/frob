+++
id = "01M47QKDM2J0EKW2TYH4N35GSV"
title = "gob-ir: markup, style and const_value answer types, queries and GRL catalog words"
type = "story"
category = "todo"
priority = "high"
points = 8
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T04:29:56Z"
updated = "2026-10-06T04:29:56Z"
scope = ["crates/gob-ir/**", "crates/gob-plan/**", "docs/design/universal-model.md", "docs/design/grl-spec.md"]

[[acceptance]]
text = "markup, style and const_value answer types exist in gob-ir with docs and the Unknown/May statuses of language-engines.md section 2"
bound = false

[[acceptance]]
text = "the GRL catalog lists element, attribute, style_rule, declaration, custom_property with their query and languages, and a GRL rule over element/attribute compiles and runs on a hand-built U term in a test"
bound = false

[[acceptance]]
text = "class_tokens returns Known tokens and Unknown for a dynamic remainder on unit-test terms"
bound = false
+++

language-engines.md sections 2 and 5. In crates/gob-ir: answer types for markup (element with tag and kind intrinsic/component/unknown, attributes with const_value values and spreads at status May, children, text), style (style rule with selector, declaration with property, raw value and component values, at-rule, custom property definition, var() reference at status May) and const_value (Known, OneOf, Fragments, Unknown with a step budget). Queries over U terms produced by any adapter; the Sigma_L operators the adapters lower to. The GRL relation catalog (grl-spec.md section 6, crates/gob-plan) gains element, attribute, style_rule, declaration and custom_property kinds with fields, each naming its query and answering languages, and the derived class_tokens query (Known tokens of class/className through clsx, cn, classnames and template literals, Unknown for the rest). Product neutral: no crunk or grimble vocabulary.
