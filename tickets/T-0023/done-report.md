## Done report

frob-check per rules.md section 4 and D27/D30: walk -> shared Inputs (graph, directives, lock, ledger) -> per-file rules in parallel with a gob-cache findings table keyed by (file digest, rule id, rule version, side-input digest incl. path, ledger tip for REF001, link-target states for DOC002) -> repo rules keyed by an inputs digest plus rule version through repo_rule -> PROC001 wrapped as a Rule -> TEST001, TICK001-003, SCOPE001 and TICK002 under --ticket (new [check] base knob) -> apply_exceptions -> sorted findings rendered with exit from fail_on; --only, --explain, --fix for Deterministic edits (tested through a test-only FIXT001 rule), [[check.tool]] stages as TOOL001 outside the budget, --timing breakdown and .frob/telemetry.jsonl, PERF001 under [perf] enforce with budget_ms; criterion bench and a fresh-process timing test (warm run 0.66 s on this repo in a debug build). check wired into the frob binary; CheckTable moved into frob-check; reference docs regenerated (37 files). Smoke on this repo: 44 errors (DSL001 v1 frob:waive comments in docs, DSL002 abbreviated ids in config comments, TEST001 symref forms in frob-ack tests, DOC002 corpus links) and 198 COV001 warnings; these are the self-host switch's cleanup list (T-0025). Deviations: run returns Result; exit 1 carries findings text in the E-NEGATIVE message because gob-cli cannot return data with a nonzero exit (follow-up); fingerprints recomputed from (rule, path, message); --ticket hops follow call edges between files rather than transitive affects; ledger config read via frob_evidence::workspace::ledger_config.

### Changed
```
 Cargo.lock                              |  37 +++
 crates/frob-check/Cargo.toml            |  51 ++++
 crates/frob-check/benches/full_check.rs |  34 +++
 crates/frob-check/src/config.rs         | 139 ++++++++++
 crates/frob-check/src/error.rs          |  35 +++
 crates/frob-check/src/filecheck.rs      | 349 ++++++++++++++++++++++++
 crates/frob-check/src/fix.rs            | 125 +++++++++
 crates/frob-check/src/lib.rs            |  63 +++++
 crates/frob-check/src/options.rs        |  34 +++
 crates/frob-check/src/pipeline.rs       | 269 +++++++++++++++++++
 crates/frob-check/src/repo.rs           | 246 +++++++++++++++++
 crates/frob-check/src/report.rs         | 169 ++++++++++++
 crates/frob-check/src/rules.rs          |  58 ++++
 crates/frob-check/src/scope.rs          | 212 +++++++++++++++
 crates/frob-check/src/snapshot.rs       | 316 ++++++++++++++++++++++
 crates/frob-check/src/store.rs          | 119 +++++++++
 crates/frob-check/src/telemetry.rs      |  49 ++++
 crates/frob-check/src/tools.rs          |  80 ++++++
 crates/frob-check/src/verb.rs           | 340 +++++++++++++++++++++++
 crates/frob-check/tests/check.rs        | 459 ++++++++++++++++++++++++++++++++
 crates/frob-check/tests/perf.rs         |  30 +++
 crates/frob/Cargo.toml                  |   3 +-
 crates/frob/src/config.rs               |  35 +--
 crates/frob/src/lib.rs                  |   5 +-
 crates/frob/tests/check_verb.rs         |  57 ++++
 docs/reference/cli/frob.md              |   1 +
 docs/reference/config.md                |  26 ++
 docs/reference/rules/COV001.md          |  92 +++++++
 docs/reference/rules/COV003.md          |  21 ++
 docs/reference/rules/DOC001.md          |  63 +++++
 docs/reference/rules/DOC002.md          |  94 +++++++
 docs/reference/rules/EXC001.md          |  51 ++++
 docs/reference/rules/EXC003.md          |  37 +++
 docs/reference/rules/EXC005.md          |  21 ++
 docs/reference/rules/EXC007.md          |  35 +++
 docs/reference/rules/INV001.md          |  45 ++++
 docs/reference/rules/INV002.md          |  68 +++++
 docs/reference/rules/PERF001.md         |  21 ++
 docs/reference/rules/PROC001.md         |  20 ++
 docs/reference/rules/README.md          |  61 +++++
 docs/reference/rules/REF001.md          |  38 +++
 docs/reference/rules/TODO001.md         |  80 ++++++
 docs/reference/rules/TODO002.md         |  36 +++
 docs/reference/rules/TOOL001.md         |  20 ++
 docs/schemas/config.json                |  64 +++++
 tickets/T-0023/ticket.md                |   6 +-
 46 files changed, 4179 insertions(+), 35 deletions(-)
```

### Evidence
(no evidence recorded)
