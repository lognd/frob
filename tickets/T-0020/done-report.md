## Done report

frob-evidence and frob-tests per tickets.md section 9 (dir: and https stores only), build-test-ci.md and audit M22/M24: EvidenceRecord events with provider nextest|command|file, blake3 digests, inline under [evidence] inline_max_bytes else the dir: store under .git/frob/artifacts, redaction via gob-log, fetch returning Unmeasured for missing blobs; EvidenceGuard implements CloseGuard (code-changing types need a Measured record, E-EVIDENCE-MISSING with remedy frob test --base, bypass recorded as an evidence-bypass event); frob-tests touched_set via gob-git diff mapped through gob-symbols, select_tests with attribute-scan test detection and a name-based caller backstop, run through gob-exec with nextest filters, frob test --base [--all] [--dry-run] recording evidence on the lease-holding ticket; TEST001. Deviations: ticket evidence is one two-word verb with the action positional (gob-cli nesting limit); evidence events are written by this crate with a re-fold because frob-ledger has no Evidence variant yet (follow-up to add EventBody::Evidence and bind accepts); knobs under [evidence]; nextest_profile knob to avoid inheriting NEXTEST_PROFILE in nested runs.

### Changed
```
 Cargo.lock                             |  44 ++++
 crates/frob-evidence/Cargo.toml        |  31 +++
 crates/frob-evidence/src/config.rs     |  27 +++
 crates/frob-evidence/src/error.rs      | 107 +++++++++
 crates/frob-evidence/src/events.rs     | 176 +++++++++++++++
 crates/frob-evidence/src/guard.rs      | 113 +++++++++
 crates/frob-evidence/src/lib.rs        |  52 +++++
 crates/frob-evidence/src/provider.rs   | 402 +++++++++++++++++++++++++++++++++
 crates/frob-evidence/src/record.rs     | 132 +++++++++++
 crates/frob-evidence/src/store.rs      | 191 ++++++++++++++++
 crates/frob-evidence/src/verbs.rs      | 340 ++++++++++++++++++++++++++++
 crates/frob-evidence/src/workspace.rs  | 132 +++++++++++
 crates/frob-evidence/tests/evidence.rs | 314 +++++++++++++++++++++++++
 crates/frob-tests/Cargo.toml           |  35 +++
 crates/frob-tests/src/catalog.rs       | 186 +++++++++++++++
 crates/frob-tests/src/error.rs         |  49 ++++
 crates/frob-tests/src/lease.rs         |  43 ++++
 crates/frob-tests/src/lib.rs           |  45 ++++
 crates/frob-tests/src/reach.rs         | 141 ++++++++++++
 crates/frob-tests/src/rule.rs          |  89 ++++++++
 crates/frob-tests/src/run.rs           | 124 ++++++++++
 crates/frob-tests/src/select.rs        | 105 +++++++++
 crates/frob-tests/src/touched.rs       | 102 +++++++++
 crates/frob-tests/src/verb.rs          | 188 +++++++++++++++
 crates/frob-tests/tests/rule.rs        |  66 ++++++
 crates/frob-tests/tests/selection.rs   | 278 +++++++++++++++++++++++
 tickets/T-0020/ticket.md               |   6 +-
 27 files changed, 3515 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)
