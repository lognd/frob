+++
id = "01M48R07X5GWGF9QN18H5W28EA"
title = "Cleanup: delete the Rule derive, Tier, RuleEntry and the rule inventory"
type = "task"
category = "todo"
priority = "low"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:11Z"
updated = "2026-10-06T13:56:11Z"
scope = ["crates/gob-rules/**", "crates/gob-macros/**"]

[[links]]
kind = "blocked-by"
target = "01M48R02V2J0R5ZXWP9MXXGNZ3"

[[links]]
kind = "blocked-by"
target = "01M48R03CM670YGJ6V3P8VPKKP"

[[links]]
kind = "blocked-by"
target = "01M48R03ZFTPSDD33HMJBD7STD"

[[links]]
kind = "blocked-by"
target = "01M48R04HAG82FJV1T77Z6YH8P"

[[links]]
kind = "blocked-by"
target = "01M48R0538K77RY0W3W6AN9XJY"

[[links]]
kind = "blocked-by"
target = "01M48R05NH09VNCDWSPJHD5710"

[[acceptance]]
text = "no rule id string literal outside id maps (grep test)"
bound = false

[[acceptance]]
text = "the derive and inventory dependency are gone from gob-rules"
bound = false
+++

M14 after every migration. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
