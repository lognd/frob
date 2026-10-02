## Done report

frob-obligations per rules.md section 2 and exceptions.md: per-file rules TODO001, DOC001, DOC002, REF001 via evaluate_file; repo rules COV001, TODO002, INV001, INV002 ([invariants] forbid_imports table) via evaluate_repo; apply_exceptions applies frob:accept and frob:defer by rule id and span, returning suppressed findings alongside EXC001 (bad reason), EXC003 (defer ticket terminal), EXC005 (accept body digest differs from frob.lock, Warn), EXC007 (defer ticket missing); COV003 registered as a never-emitted alias of TEST001 owned by frob-tests; mdtest corpora for ten rules plus multi-file repo tests. Deviations to reconcile in T-0029: EXC numbering follows the milestone-1 ticket rather than exceptions.md section 6; flagged exceptions still suppress (the EXC finding fails the gate); until= not evaluated yet; comment discovery duplicated from gob-directives pending an exported API.

### Changed
```
 Cargo.lock                                      |  25 ++
 crates/frob-obligations/Cargo.toml              |  36 +++
 crates/frob-obligations/src/collect.rs          | 106 ++++++++
 crates/frob-obligations/src/comments.rs         | 194 +++++++++++++
 crates/frob-obligations/src/config.rs           |  42 +++
 crates/frob-obligations/src/cov.rs              | 154 +++++++++++
 crates/frob-obligations/src/doc.rs              | 316 ++++++++++++++++++++++
 crates/frob-obligations/src/exc.rs              | 239 ++++++++++++++++
 crates/frob-obligations/src/inv.rs              | 197 ++++++++++++++
 crates/frob-obligations/src/lib.rs              | 263 ++++++++++++++++++
 crates/frob-obligations/src/refs.rs             |  38 +++
 crates/frob-obligations/src/rules.rs            | 251 +++++++++++++++++
 crates/frob-obligations/src/tickets.rs          |  70 +++++
 crates/frob-obligations/src/todo.rs             | 128 +++++++++
 crates/frob-obligations/src/util.rs             |  26 ++
 crates/frob-obligations/tests/common/mod.rs     | 109 ++++++++
 crates/frob-obligations/tests/corpus.rs         |  32 +++
 crates/frob-obligations/tests/mdtest/cov001.md  |  69 +++++
 crates/frob-obligations/tests/mdtest/doc001.md  |  42 +++
 crates/frob-obligations/tests/mdtest/doc002.md  |  72 +++++
 crates/frob-obligations/tests/mdtest/exc001.md  |  30 +++
 crates/frob-obligations/tests/mdtest/exc003.md  |  16 ++
 crates/frob-obligations/tests/mdtest/exc007.md  |  16 ++
 crates/frob-obligations/tests/mdtest/inv001.md  |  24 ++
 crates/frob-obligations/tests/mdtest/inv002.md  |  36 +++
 crates/frob-obligations/tests/mdtest/ref001.md  |  18 ++
 crates/frob-obligations/tests/mdtest/todo001.md |  58 ++++
 crates/frob-obligations/tests/mdtest/todo002.md |  16 ++
 crates/frob-obligations/tests/repo.rs           | 345 ++++++++++++++++++++++++
 tickets/T-0022/ticket.md                        |   6 +-
 30 files changed, 2971 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)
