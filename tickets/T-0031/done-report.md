## Done report

Wires frob-lease, frob-worktree, frob-evidence, frob-tests and frob-ack into the frob binary: all register functions called in frob::cli (verbs lease list, ticket contention, work, start, requeue, ticket evidence, test, ack, graph why, graph affects); ticket close installs EvidenceGuard with --no-evidence --reason bypass audited as an evidence-bypass event; ticket doable uses LeaseGuard with a warned fallback; [lease], [worktree], [evidence] tables validated through FrobConfig; [tickets] registry_files accepted as a compatibility alias folded into [lease] shared_files (honoured by doable only until frob-lease takes a config); reference docs regenerated (21 files). Limitations recorded: --schema does not waive required positionals in gob-cli; the alias does not reach frob work or lease list.

### Changed
```
 Cargo.lock                        |   5 +
 crates/frob/Cargo.toml            |   7 +-
 crates/frob/src/config.rs         |  40 +++++++-
 crates/frob/src/lib.rs            |  12 ++-
 crates/frob/src/ticket/read.rs    |  46 ++++++++-
 crates/frob/src/ticket/write.rs   |  33 ++++++-
 crates/frob/tests/cli.rs          |  10 ++
 crates/frob/tests/ticket.rs       |   4 +-
 crates/frob/tests/wiring.rs       | 202 ++++++++++++++++++++++++++++++++++++++
 docs/reference/cli/frob.md        |  24 +++++
 docs/reference/config.md          |  41 ++++++++
 docs/reference/rules/AFFECT001.md |  23 +++++
 docs/reference/rules/DRIFT001.md  |  23 +++++
 docs/reference/rules/DRIFT002.md  |  19 ++++
 docs/reference/rules/DRIFT003.md  |  20 ++++
 docs/reference/rules/README.md    |  34 +++++++
 docs/reference/rules/SCOPE001.md  |  20 ++++
 docs/reference/rules/TEST001.md   |  20 ++++
 docs/reference/rules/TICK001.md   |  20 ++++
 docs/reference/rules/TICK002.md   |  19 ++++
 docs/reference/rules/TICK003.md   |  18 ++++
 docs/schemas/config.json          | 115 ++++++++++++++++++++++
 tickets/T-0031/ticket.md          |   6 +-
 23 files changed, 744 insertions(+), 17 deletions(-)
```

### Evidence
(no evidence recorded)
