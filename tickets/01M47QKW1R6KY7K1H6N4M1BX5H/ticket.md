+++
id = "01M47QKW1R6KY7K1H6N4M1BX5H"
title = "Web conformance corpus: TS, TSX, CSS, HTML fixtures and capability-matrix rows end to end"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T04:30:11Z"
updated = "2026-10-06T11:54:52Z"
scope = ["crates/gob-symbols/**", "crates/gob-languages/**", "crates/frob/tests/**", "crates/grimble/tests/**", "crates/crunk/tests/**", "docs/reference/**", "crates/frob/Cargo.toml", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M43ARY26XF7A4MSRAZ8V73JM"

[[links]]
kind = "blocked-by"
target = "01M47QKSBYX7YFQHV3VVGKB025"

[[links]]
kind = "blocked-by"
target = "01M47QKT10CG0RSF784EEYTQ0J"

[[links]]
kind = "blocked-by"
target = "01M47QKVBB5G9N1QZP3AVXTRHX"

[[acceptance]]
text = "each web language has a conformance fixture directory checked by the capability-matrix test"
bound = true

[[acceptance]]
text = "the generated languages page lists ts, tsx, js, jsx, css, html with their cells"
bound = true

[[acceptance]]
text = "the three products check one shared TSX/CSS fixture repository in an integration test"
bound = true
+++

language-engines.md section 5 and code-model.md section 3 (fidelity corpus). One corpus per web language with expected symbols, imports, markup, style and digests, the capability-matrix cells per language (Implemented, NotApplicable with reason, Gap with ticket), and an end-to-end frob check, grimble check and crunk check over one TSX/CSS fixture repository.
