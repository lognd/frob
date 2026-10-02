## Done report

gob-log per architecture.md section 5: tracing-subscriber init with FROB_LOG (the one diagnostic env var), human or JSON stderr layers, span close timing, AlreadyInitialized error on a second init; redact() masks bearer tokens, AWS AKIA/ASIA keys, GitHub token prefixes, URL userinfo and TOKEN/SECRET/PASSWORD key-value pairs with [REDACTED]; testing::capture helper behind cfg(test) or the test-util feature. Deviations: bearer keyword kept visible; broader token patterns than the exact 36-char form; init emits one debug event; FROB_LOG env read is covered via build_filter unit tests rather than env mutation.

### Changed
```
 Cargo.lock                    | 293 +++++++++++++++++++++++++++++++++++++++++-
 crates/gob-log/Cargo.toml     |  23 ++++
 crates/gob-log/src/init.rs    | 130 +++++++++++++++++++
 crates/gob-log/src/lib.rs     |  16 +++
 crates/gob-log/src/redact.rs  | 118 +++++++++++++++++
 crates/gob-log/src/testing.rs | 103 +++++++++++++++
 tickets/T-0007/ticket.md      |   6 +-
 7 files changed, 685 insertions(+), 4 deletions(-)
```

### Evidence
(no evidence recorded)
