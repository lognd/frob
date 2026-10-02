## Done report

gob-exec per git-io.md section 3 and architecture.md section 9: Program allowlist enum (Git, Cargo, Hook{path}, Sibling, Tool), Spec/Runner with a std semaphore bounding concurrent children, timeout killing the unix process group via nix signal, redacted captured output through gob-log, per-runner, per-thread and global spawn counters with an assert_spawns helper, ExecError via thiserror. PROC001 is a plain scan function over crates/*/src pending the Rule derive from T-0005. Deviations: Hook carries a path; Sibling resolves next to current_exe first; Tool names are open by default with Runner::allow_tools to restrict; Output has a started timestamp.

### Changed
```
 Cargo.lock                            | 335 ++++++++++++++++++++++++++++++++++
 crates/gob-exec/Cargo.toml            |  23 +++
 crates/gob-exec/src/counter.rs        |  48 +++++
 crates/gob-exec/src/error.rs          |  26 +++
 crates/gob-exec/src/lib.rs            |  21 +++
 crates/gob-exec/src/proc001.rs        | 144 +++++++++++++++
 crates/gob-exec/src/program.rs        |  92 ++++++++++
 crates/gob-exec/src/runner.rs         | 224 +++++++++++++++++++++++
 crates/gob-exec/src/semaphore.rs      |  46 +++++
 crates/gob-exec/tests/proc001_self.rs |  10 +
 crates/gob-exec/tests/runner.rs       | 180 ++++++++++++++++++
 tickets/T-0009/ticket.md              |   6 +-
 12 files changed, 1152 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)
