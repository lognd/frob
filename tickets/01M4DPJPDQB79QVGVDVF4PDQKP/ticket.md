+++
id = "01M4DPJPDQB79QVGVDVF4PDQKP"
title = "gob-symbols CSS: '! important', '!IMPORTANT' and empty '--x:;' are not syntax errors"
type = "bug"
category = "todo"
priority = "medium"
points = 1
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-08T12:07:31Z"
updated = "2026-10-08T12:07:31Z"
scope = ["changelog.d/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "Given those three forms, when parsed, then no syntax error is reported and the declarations are facts"
bound = false
+++

Follow-up from ~HRHS033 (Python crunk accepted them).
