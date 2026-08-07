## Done report

Moved 30 files via git mv: guides/ (2), commands/ (9), modules/ (19);
index.md + rework.md stay at root; strata/ untouched. One global rewrite
pass updated every reference in 179 tracked files (frob:doc directives,
backtick doc links, README, TODO.md, pyproject.toml, agents/, skills/,
scripts/, invariants/, frob-core comments). 17 E501s introduced by the
longer paths fixed by wrapping at the doc parenthetical -- doc-facet
digests unaffected because doc_text is whitespace-collapsed by design.
Acceptance verified: frob graph build clean (edges stable at 1311, zero
dangling), frob check --ticket T-0088 exit 0 (doclink/drift/coverage all
pass), frob test --base main --lang python PASS, cargo test --lib 13/13
PASS.
