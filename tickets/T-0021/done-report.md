## Done report

gob-lock (product-parametric TOML lock file with sorted entries, atomic save, diff) and frob-ack per code-model.md sections 2 and 6 and D28: Inputs::collect builds the symbol graph, frob.lock and frob:doc directive records with per-file artifact caching (warm 0.26 s on this workspace); ack and plan_ack record current digests and commit frob.lock on the current branch via commit_paths; verbs ack, graph why, graph affects via register(Cli) -> Cli; DRIFT001 per drifted facet, DRIFT002 with nearest heading, DRIFT003 stale ack on sig change, AFFECT001 public sig change with dependents lacking a later ack; evaluate() cached in repo_rule keyed by inputs digest plus rule version. Deviations: lock entries carry a targets vector; register consumes Cli like ticket::register; graph affects includes the file node.

### Changed
```
 Cargo.lock                         |  37 ++++
 crates/frob-ack/Cargo.toml         |  37 ++++
 crates/frob-ack/src/ack.rs         | 221 ++++++++++++++++++++++
 crates/frob-ack/src/cmd.rs         | 377 +++++++++++++++++++++++++++++++++++++
 crates/frob-ack/src/error.rs       |  72 +++++++
 crates/frob-ack/src/inputs.rs      | 204 ++++++++++++++++++++
 crates/frob-ack/src/lib.rs         |  36 ++++
 crates/frob-ack/src/repo_rule.rs   |  91 +++++++++
 crates/frob-ack/src/rules.rs       | 359 +++++++++++++++++++++++++++++++++++
 crates/frob-ack/tests/ack.rs       | 339 +++++++++++++++++++++++++++++++++
 crates/frob-ack/tests/workspace.rs |  33 ++++
 crates/gob-lock/Cargo.toml         |  22 +++
 crates/gob-lock/src/diff.rs        |  92 +++++++++
 crates/gob-lock/src/file.rs        | 212 +++++++++++++++++++++
 crates/gob-lock/src/lib.rs         |  24 +++
 crates/gob-lock/tests/lock.rs      |  64 +++++++
 tickets/T-0021/ticket.md           |   6 +-
 17 files changed, 2223 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)
