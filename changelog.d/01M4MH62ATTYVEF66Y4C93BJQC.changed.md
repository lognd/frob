Cargo fmt and clippy stages of a scoped check now run over the changed crates and their direct dependents, widening to all transitive dependents only when a crate's public API changed.
